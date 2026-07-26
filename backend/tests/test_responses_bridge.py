"""Unit tests for Responses ↔ Chat Completions bridge."""
from __future__ import annotations

import json
import unittest

from infra.responses_bridge import (
    ChatToResponsesStream,
    chat_completion_to_response,
    responses_request_to_chat,
)


class ResponsesBridgeTests(unittest.TestCase):
    def test_string_input_to_chat_messages(self) -> None:
        chat = responses_request_to_chat(
            {"model": "deepseek-v4-flash", "input": "hello", "instructions": "be brief"}
        )
        self.assertEqual(chat["model"], "deepseek-v4-flash")
        self.assertEqual(chat["messages"][0], {"role": "system", "content": "be brief"})
        self.assertEqual(chat["messages"][1], {"role": "user", "content": "hello"})

    def test_chat_completion_to_response_text(self) -> None:
        resp = chat_completion_to_response(
            {
                "id": "chatcmpl-1",
                "object": "chat.completion",
                "created": 1,
                "model": "deepseek-v4-flash",
                "choices": [{"message": {"role": "assistant", "content": "hi"}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
            },
            model="deepseek-v4-flash",
        )
        self.assertEqual(resp["object"], "response")
        self.assertEqual(resp["status"], "completed")
        self.assertEqual(resp["output"][0]["content"][0]["text"], "hi")
        self.assertEqual(resp["usage"]["total_tokens"], 4)

    def test_non_function_tools_are_dropped(self) -> None:
        chat = responses_request_to_chat(
            {
                "model": "deepseek-v4-flash",
                "input": "hi",
                "tools": [
                    {"type": "function", "name": "shell", "parameters": {"type": "object"}},
                    {"type": "web_search"},
                    {"type": "local_shell"},
                    {"type": "custom", "name": "apply_patch", "format": {"type": "grammar"}},
                ],
            }
        )
        self.assertEqual(len(chat["tools"]), 1)
        self.assertEqual(chat["tools"][0]["function"]["name"], "shell")

    def test_only_non_function_tools_omits_tools_key(self) -> None:
        chat = responses_request_to_chat(
            {"model": "m", "input": "hi", "tools": [{"type": "web_search"}], "tool_choice": "auto"}
        )
        self.assertNotIn("tools", chat)
        self.assertNotIn("tool_choice", chat)

    def test_tool_result_follows_assistant_tool_calls(self) -> None:
        # Codex sends: function_call, assistant message, function_call_output.
        # Chat upstreams require the tool message directly after tool_calls.
        chat = responses_request_to_chat(
            {
                "model": "m",
                "input": [
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "count files"}]},
                    {"type": "function_call", "call_id": "call_1", "name": "exec_command", "arguments": "{}"},
                    {"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "running ls"}]},
                    {"type": "function_call_output", "call_id": "call_1", "output": "10"},
                ],
            }
        )
        roles = [m["role"] for m in chat["messages"]]
        self.assertEqual(roles, ["user", "assistant", "tool", "assistant"])
        self.assertEqual(chat["messages"][1]["tool_calls"][0]["id"], "call_1")
        self.assertEqual(chat["messages"][2]["tool_call_id"], "call_1")
        # DeepSeek thinking mode requires this field on assistant tool turns.
        self.assertEqual(chat["messages"][1].get("reasoning_content"), "")

    def test_assistant_tool_calls_get_empty_reasoning_content(self) -> None:
        chat = responses_request_to_chat(
            {
                "model": "deepseek-v4-flash",
                "input": [
                    {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hi"}]},
                    {
                        "type": "function_call",
                        "call_id": "call_00_abc",
                        "name": "shell",
                        "arguments": '{"cmd":"ls"}',
                    },
                    {"type": "function_call_output", "call_id": "call_00_abc", "output": "ok"},
                ],
            }
        )
        assistant = next(m for m in chat["messages"] if m.get("tool_calls"))
        self.assertEqual(assistant["reasoning_content"], "")

    def test_bare_json_error_line_emits_failed(self) -> None:
        translator = ChatToResponsesStream(model="m")
        events = translator.feed_line(
            '{"error":{"message":"unknown variant `web_search`","type":"invalid_request_error"}}'
        )
        joined = "\n".join(e.decode("utf-8") for e in events)
        self.assertIn("response.failed", joined)
        self.assertIn("response.completed", joined)
        self.assertIn("unknown variant", joined)
        self.assertTrue(translator.finished)

    def test_stream_translator_emits_completed(self) -> None:
        translator = ChatToResponsesStream(model="deepseek-v4-flash")
        events = []
        events.extend(
            translator.feed_line(
                'data: {"choices":[{"delta":{"content":"你好"},"index":0}]}'
            )
        )
        events.extend(translator.feed_line("data: [DONE]"))
        events.extend(translator.finish(usage={"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}))
        decoded = [e.decode("utf-8") for e in events]
        joined = "\n".join(decoded)
        self.assertIn("event: response.created", joined)
        self.assertIn("response.output_text.delta", joined)
        self.assertIn("response.completed", joined)
        # Ensure deltas carry text
        delta_payloads = [
            json.loads(block.split("data: ", 1)[1].split("\n", 1)[0])
            for block in decoded
            if "response.output_text.delta" in block and "data: " in block
        ]
        self.assertTrue(any(p.get("delta") == "你好" for p in delta_payloads))


if __name__ == "__main__":
    unittest.main()
