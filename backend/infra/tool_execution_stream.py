"""工具执行流 — 每次 tool_result 立即持久化，一字不少

不管任务完成/失败/超时/崩溃，全量监控。路径与 task_history 同目录。
"""
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("evotown.tool_execution_stream")

_backend_dir = Path(__file__).resolve().parent.parent
_evotown_data = _backend_dir.parent / "data"
_DATA_DIR = Path(os.environ.get("EVOTOWN_DATA_DIR", _evotown_data if _evotown_data.is_dir() else _backend_dir / "data"))
_STREAM_PATH = _DATA_DIR / "tool_execution_stream.jsonl"


def _ensure_dir() -> None:
    _STREAM_PATH.parent.mkdir(parents=True, exist_ok=True)


def append_tool_entry(
    agent_id: str,
    task_text: str,
    task_id: str,
    name: str,
    arguments: str,
    result: str,
    is_error: bool,
) -> None:
    """每次 tool_result 到达时立即追加，完整保留 arguments 和 result，一字不少"""
    record = {
        "ts": time.time(),
        "agent_id": agent_id,
        "task": (task_text or "")[:500],
        "task_id": task_id or "",
        "name": name,
        "arguments": arguments,  # 完整参数
        "result": result,       # 完整结果
        "is_error": is_error,
    }
    try:
        _ensure_dir()
        with open(_STREAM_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as e:
        logger.warning("Failed to append tool entry: %s", e)


def load_execution_log_for_task(
    agent_id: str,
    task_text: str,
    task_id: str | None = None,
    limit: int = 10000,
) -> list[dict[str, Any]]:
    """按 agent_id + task 加载执行明细，返回 [{name, arguments, result, is_error}, ...]"""
    if not _STREAM_PATH.exists():
        return []
    task_clean = (task_text or "").strip()
    if not task_clean:
        return []
    entries: list[dict[str, Any]] = []
    try:
        with open(_STREAM_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    if r.get("agent_id") != agent_id:
                        continue
                    t = (r.get("task") or "").strip()
                    if not t or (task_clean not in t and t not in task_clean):
                        continue
                    if task_id and r.get("task_id") and r.get("task_id") != task_id:
                        continue
                    entries.append({
                        "name": r.get("name", ""),
                        "arguments": r.get("arguments", ""),
                        "result": r.get("result"),
                        "is_error": r.get("is_error", False),
                    })
                except json.JSONDecodeError:
                    continue
        return entries[-limit:] if limit else entries
    except OSError as e:
        logger.warning("Failed to load tool execution stream: %s", e)
        return []
