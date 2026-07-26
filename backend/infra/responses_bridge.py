"""Bridge OpenAI Responses API ↔ Chat Completions for Codex-compatible gateways.

Many upstreams (DeepSeek, etc.) only expose /chat/completions. Codex CLI now
requires wire_api=responses, so Evotown fulfills /responses by translating.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any


def responses_request_to_chat(body: dict[str, Any]) -> dict[str, Any]:
    """Convert a Responses API request into a Chat Completions request."""
    messages: list[dict[str, Any]] = []
    instructions = body.get("instructions")
    if isinstance(instructions, str) and instructions.strip():
        messages.append({"role": "system", "content": instructions})

    raw_input = body.get("input")
    if isinstance(raw_input, str):
        if raw_input.strip():
            messages.append({"role": "user", "content": raw_input})
    elif isinstance(raw_input, list):
        for item in raw_input:
            messages.extend(_input_item_to_messages(item))
    elif isinstance(body.get("messages"), list):
        # Already chat-shaped (some clients mix formats).
        for message in body["messages"]:
            if isinstance(message, dict):
                messages.append(message)

    messages = _reorder_tool_messages(messages)
    # DeepSeek thinking models reject follow-up tool turns unless every
    # assistant message that carries tool_calls also includes reasoning_content.
    # Codex/Responses clients do not round-trip that field, so inject "" when missing.
    _ensure_assistant_tool_reasoning(messages)

    if not messages:
        messages.append({"role": "user", "content": ""})

    chat: dict[str, Any] = {
        "model": body.get("model"),
        "messages": messages,
        "stream": bool(body.get("stream")),
    }

    for key in ("temperature", "top_p", "presence_penalty", "frequency_penalty", "stop", "user"):
        if key in body:
            chat[key] = body[key]

    if "max_output_tokens" in body:
        chat["max_tokens"] = body["max_output_tokens"]
    elif "max_tokens" in body:
        chat["max_tokens"] = body["max_tokens"]

    tools = body.get("tools")
    if isinstance(tools, list) and tools:
        # Drop tools that have no Chat Completions equivalent (web_search,
        # local_shell, custom grammar tools, ...): upstreams reject the whole
        # request on any unknown tool type.
        chat_tools = [t for t in (_tool_to_chat(tool) for tool in tools) if t is not None]
        if chat_tools:
            chat["tools"] = chat_tools
    if "tool_choice" in body and chat.get("tools"):
        tool_choice = body["tool_choice"]
        if isinstance(tool_choice, str) or (
            isinstance(tool_choice, dict) and tool_choice.get("type") == "function"
        ):
            chat["tool_choice"] = tool_choice

    return chat


def chat_completion_to_response(data: dict[str, Any], *, model: str) -> dict[str, Any]:
    """Convert a Chat Completions JSON response into a Responses API object."""
    response_id = f"resp_{uuid.uuid4().hex}"
    created = int(data.get("created") or time.time())
    choice = {}
    choices = data.get("choices")
    if isinstance(choices, list) and choices and isinstance(choices[0], dict):
        choice = choices[0]
    message = choice.get("message") if isinstance(choice.get("message"), dict) else {}
    content = message.get("content")
    text = content if isinstance(content, str) else ""
    tool_calls = message.get("tool_calls") if isinstance(message.get("tool_calls"), list) else []

    output: list[dict[str, Any]] = []
    if tool_calls:
        for index, call in enumerate(tool_calls):
            if not isinstance(call, dict):
                continue
            fn = call.get("function") if isinstance(call.get("function"), dict) else {}
            output.append(
                {
                    "type": "function_call",
                    "id": str(call.get("id") or f"fc_{index}"),
                    "call_id": str(call.get("id") or f"call_{index}"),
                    "name": str(fn.get("name") or ""),
                    "arguments": str(fn.get("arguments") or ""),
                }
            )
    else:
        output.append(
            {
                "type": "message",
                "id": f"msg_{uuid.uuid4().hex}",
                "role": "assistant",
                "status": "completed",
                "content": [{"type": "output_text", "text": text}],
            }
        )

    usage_in = data.get("usage") if isinstance(data.get("usage"), dict) else {}
    return {
        "id": response_id,
        "object": "response",
        "created_at": created,
        "status": "completed",
        "model": data.get("model") or model,
        "output": output,
        "usage": {
            "input_tokens": int(usage_in.get("prompt_tokens") or 0),
            "output_tokens": int(usage_in.get("completion_tokens") or 0),
            "total_tokens": int(usage_in.get("total_tokens") or 0),
        },
    }


class ChatToResponsesStream:
    """Stateful translator from Chat Completions SSE lines to Responses SSE events."""

    def __init__(self, *, model: str) -> None:
        self.model = model
        self.response_id = f"resp_{uuid.uuid4().hex}"
        self.item_id = f"msg_{uuid.uuid4().hex}"
        self.seq = 0
        self.started = False
        self.text = ""
        self.reasoning = ""
        self.finished = False
        # tool_calls index -> accumulated call
        self.tool_calls: dict[int, dict[str, Any]] = {}

    def _next_seq(self) -> int:
        self.seq += 1
        return self.seq

    def _event(self, event_type: str, payload: dict[str, Any]) -> bytes:
        body = {"type": event_type, "sequence_number": self._next_seq(), **payload}
        # Include both `event:` and `data:` — Codex expects Responses SSE envelope.
        return f"event: {event_type}\ndata: {json.dumps(body, ensure_ascii=False)}\n\n".encode("utf-8")

    def _ensure_started(self) -> list[bytes]:
        if self.started:
            return []
        self.started = True
        created = {
            "id": self.response_id,
            "object": "response",
            "created_at": int(time.time()),
            "status": "in_progress",
            "model": self.model,
            "output": [],
        }
        return [
            self._event("response.created", {"response": created}),
            self._event("response.in_progress", {"response": {**created, "status": "in_progress"}}),
            self._event(
                "response.output_item.added",
                {
                    "output_index": 0,
                    "item": {
                        "type": "message",
                        "id": self.item_id,
                        "role": "assistant",
                        "status": "in_progress",
                        "content": [],
                    },
                },
            ),
            self._event(
                "response.content_part.added",
                {
                    "item_id": self.item_id,
                    "output_index": 0,
                    "content_index": 0,
                    "part": {"type": "output_text", "text": ""},
                },
            ),
        ]

    def feed_line(self, line: str) -> list[bytes]:
        line = line.strip()
        if not line or self.finished:
            return []
        if line.startswith("data:"):
            data = line[5:].strip()
        elif line.startswith("{"):
            # Some upstreams return a bare JSON error body with HTTP 200
            # instead of an SSE `data:` line.
            data = line
        else:
            return []
        if data == "[DONE]":
            return []
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            return []
        if not isinstance(payload, dict):
            return []
        if payload.get("error"):
            err = payload["error"]
            message = err.get("message") if isinstance(err, dict) else str(err)
            self.finished = True
            failed = {
                "id": self.response_id,
                "object": "response",
                "status": "failed",
                "model": self.model,
                "output": [],
                "error": {"message": message or "upstream error"},
            }
            # Emit both failed and completed(status=failed): Codex CLI errors with
            # "stream closed before response.completed" if the stream ends on failed alone.
            return [
                self._event("response.failed", {"response": failed}),
                self._event("response.completed", {"response": failed}),
            ]

        events = self._ensure_started()
        choices = payload.get("choices")
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            delta = choices[0].get("delta") if isinstance(choices[0].get("delta"), dict) else {}

            # DeepSeek-style reasoning tokens — keep as fallback visible text if
            # the model never emits final `content`.
            reason = delta.get("reasoning_content")
            if isinstance(reason, str) and reason:
                self.reasoning += reason

            piece = delta.get("content")
            if isinstance(piece, str) and piece:
                self.text += piece
                events.append(
                    self._event(
                        "response.output_text.delta",
                        {
                            "item_id": self.item_id,
                            "output_index": 0,
                            "content_index": 0,
                            "delta": piece,
                        },
                    )
                )

            # Accumulate streamed tool_calls (Chat Completions shape).
            tool_deltas = delta.get("tool_calls")
            if isinstance(tool_deltas, list):
                for td in tool_deltas:
                    if not isinstance(td, dict):
                        continue
                    idx = int(td.get("index") or 0)
                    slot = self.tool_calls.setdefault(
                        idx,
                        {"id": "", "name": "", "arguments": ""},
                    )
                    if td.get("id"):
                        slot["id"] = str(td["id"])
                    fn = td.get("function") if isinstance(td.get("function"), dict) else {}
                    if fn.get("name"):
                        slot["name"] = str(fn["name"])
                    if fn.get("arguments"):
                        slot["arguments"] += str(fn["arguments"])
        return events

    def finish(self, usage: Any = None) -> list[bytes]:
        if self.finished:
            return []
        self.finished = True
        events = self._ensure_started()

        # If upstream only streamed reasoning (common on some DeepSeek turns),
        # surface it so Codex is not left with an empty assistant message.
        if not self.text.strip() and self.reasoning.strip():
            self.text = self.reasoning.strip()
            events.append(
                self._event(
                    "response.output_text.delta",
                    {
                        "item_id": self.item_id,
                        "output_index": 0,
                        "content_index": 0,
                        "delta": self.text,
                    },
                )
            )

        output_items: list[dict[str, Any]] = []
        if self.tool_calls:
            for idx in sorted(self.tool_calls):
                call = self.tool_calls[idx]
                call_id = call["id"] or f"call_{idx}"
                item = {
                    "type": "function_call",
                    "id": f"fc_{idx}",
                    "call_id": call_id,
                    "name": call["name"],
                    "arguments": call["arguments"],
                }
                output_items.append(item)
                events.append(
                    self._event(
                        "response.output_item.added",
                        {"output_index": len(output_items), "item": {**item, "status": "in_progress"}},
                    )
                )
                events.append(
                    self._event(
                        "response.output_item.done",
                        {"output_index": len(output_items), "item": item},
                    )
                )

        events.extend(
            [
                self._event(
                    "response.output_text.done",
                    {
                        "item_id": self.item_id,
                        "output_index": 0,
                        "content_index": 0,
                        "text": self.text,
                    },
                ),
                self._event(
                    "response.content_part.done",
                    {
                        "item_id": self.item_id,
                        "output_index": 0,
                        "content_index": 0,
                        "part": {"type": "output_text", "text": self.text},
                    },
                ),
                self._event(
                    "response.output_item.done",
                    {
                        "output_index": 0,
                        "item": {
                            "type": "message",
                            "id": self.item_id,
                            "role": "assistant",
                            "status": "completed",
                            "content": [{"type": "output_text", "text": self.text}],
                        },
                    },
                ),
            ]
        )
        usage_in = usage if isinstance(usage, dict) else {}
        message_item = {
            "type": "message",
            "id": self.item_id,
            "role": "assistant",
            "status": "completed",
            "content": [{"type": "output_text", "text": self.text}],
        }
        completed_output = [message_item, *output_items] if self.text.strip() or not output_items else output_items
        if self.text.strip() and output_items:
            completed_output = [message_item, *output_items]
        elif output_items and not self.text.strip():
            completed_output = output_items
        else:
            completed_output = [message_item]

        completed = {
            "id": self.response_id,
            "object": "response",
            "created_at": int(time.time()),
            "status": "completed",
            "model": self.model,
            "output": completed_output,
            "usage": {
                "input_tokens": int(usage_in.get("prompt_tokens") or 0),
                "output_tokens": int(usage_in.get("completion_tokens") or 0),
                "total_tokens": int(usage_in.get("total_tokens") or 0),
            },
        }
        events.append(self._event("response.completed", {"response": completed}))
        return events


def _input_item_to_messages(item: Any) -> list[dict[str, Any]]:
    if isinstance(item, str):
        return [{"role": "user", "content": item}] if item.strip() else []
    if not isinstance(item, dict):
        return []

    item_type = str(item.get("type") or "").lower()
    role = str(item.get("role") or "").lower()

    if item_type in {"function_call_output", "tool_result"}:
        return [
            {
                "role": "tool",
                "tool_call_id": str(item.get("call_id") or item.get("id") or ""),
                "content": str(item.get("output") or item.get("content") or ""),
            }
        ]

    if item_type == "function_call":
        return [
            {
                "role": "assistant",
                "content": None,
                # Required by DeepSeek thinking mode on tool-call turns.
                "reasoning_content": "",
                "tool_calls": [
                    {
                        "id": str(item.get("call_id") or item.get("id") or f"call_{uuid.uuid4().hex[:8]}"),
                        "type": "function",
                        "function": {
                            "name": str(item.get("name") or ""),
                            "arguments": str(item.get("arguments") or ""),
                        },
                    }
                ],
            }
        ]

    if role in {"user", "assistant", "system", "tool", "developer"}:
        content = item.get("content")
        if isinstance(content, list):
            parts: list[str] = []
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text") or block.get("output_text") or block.get("input_text")
                    if text:
                        parts.append(str(text))
                elif isinstance(block, str):
                    parts.append(block)
            content = "\n".join(parts)
        mapped_role = "system" if role == "developer" else role
        return [{"role": mapped_role, "content": content if isinstance(content, str) else str(content or "")}]

    if item_type in {"message", ""}:
        content = item.get("content")
        if isinstance(content, str) and content.strip():
            return [{"role": "user", "content": content}]
    return []


def _ensure_assistant_tool_reasoning(messages: list[dict[str, Any]]) -> None:
    """Ensure assistant tool_calls messages include reasoning_content.

    DeepSeek V3/V4 thinking mode returns:
      The `reasoning_content` in the thinking mode must be passed back to the API.
    when a prior assistant turn had tool_calls but the follow-up omits the field.
    Empty string is accepted and keeps Codex (Responses API) working.
    """
    for message in messages:
        if message.get("role") != "assistant":
            continue
        tool_calls = message.get("tool_calls")
        if not isinstance(tool_calls, list) or not tool_calls:
            continue
        if "reasoning_content" not in message:
            message["reasoning_content"] = ""


def responses_stream_error_events(*, model: str, message: str) -> list[bytes]:
    """Emit Responses SSE terminal failure events Codex can consume.

    Bare `data: {"error":...}` without `response.failed` / completion causes:
      stream disconnected before completion: stream closed before response.completed
    """
    translator = ChatToResponsesStream(model=model or "unknown")
    return translator.feed_line(json.dumps({"error": {"message": message}}))


def _reorder_tool_messages(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Ensure tool messages immediately follow their assistant tool_calls message.

    Codex interleaves items (function_call, assistant text, function_call_output),
    but Chat Completions upstreams require each `tool` message to directly follow
    the assistant message that declared its tool_call_id.
    """
    tool_by_call_id: dict[str, dict[str, Any]] = {}
    for message in messages:
        if message.get("role") == "tool" and message.get("tool_call_id"):
            tool_by_call_id[str(message["tool_call_id"])] = message

    consumed: set[int] = set()
    ordered: list[dict[str, Any]] = []
    for message in messages:
        if message.get("role") == "tool" and id(message) in consumed:
            continue
        if message.get("role") == "tool" and str(message.get("tool_call_id") or "") in tool_by_call_id:
            # Leave unmatched/orphan tool messages in place; matched ones are
            # emitted right after their assistant message below.
            matched_assistant = any(
                isinstance(m.get("tool_calls"), list)
                and any(
                    isinstance(tc, dict) and str(tc.get("id")) == str(message.get("tool_call_id"))
                    for tc in m["tool_calls"]
                )
                for m in messages
                if m.get("role") == "assistant"
            )
            if matched_assistant:
                continue
        ordered.append(message)
        if message.get("role") == "assistant" and isinstance(message.get("tool_calls"), list):
            for call in message["tool_calls"]:
                if not isinstance(call, dict):
                    continue
                tool_message = tool_by_call_id.get(str(call.get("id")))
                if tool_message is not None and id(tool_message) not in consumed:
                    ordered.append(tool_message)
                    consumed.add(id(tool_message))
    return ordered


def _tool_to_chat(tool: Any) -> dict[str, Any] | None:
    """Convert a Responses tool definition to Chat Completions, or None if impossible."""
    if not isinstance(tool, dict):
        return None
    if tool.get("type") == "function" and isinstance(tool.get("function"), dict):
        return tool
    # Responses-style flat tool: {type:"function", name, description, parameters}
    if tool.get("type") == "function" and tool.get("name"):
        return {
            "type": "function",
            "function": {
                "name": str(tool.get("name")),
                "description": str(tool.get("description") or ""),
                "parameters": tool.get("parameters") or {},
            },
        }
    return None
