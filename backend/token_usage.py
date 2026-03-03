"""Evotown Token 消耗统计 — 仅统计本进程内 llm_client 的 LLM 调用

注意：Agent 执行任务时的 LLM 调用在子进程中，不包含在此统计内。
"""
import threading
from dataclasses import dataclass, field


@dataclass
class TokenUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


_usage = TokenUsage()
_lock = threading.Lock()


def add_usage(prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
    """累加一次 LLM 调用的 token 消耗"""
    with _lock:
        _usage.prompt_tokens += prompt_tokens
        _usage.completion_tokens += completion_tokens


def get_usage() -> dict:
    """返回当前累计的 token 统计（供 API 使用）"""
    with _lock:
        return {
            "prompt_tokens": _usage.prompt_tokens,
            "completion_tokens": _usage.completion_tokens,
            "total_tokens": _usage.total_tokens,
        }
