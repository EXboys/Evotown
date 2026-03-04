"""Replay 录制器 — 把所有 WS 广播事件写入 JSONL，供回放使用"""
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("evotown.replay")

REPLAY_DIR = Path(__file__).parent.parent / "replays"


def _ensure_dir() -> Path:
    REPLAY_DIR.mkdir(parents=True, exist_ok=True)
    return REPLAY_DIR


class ReplayRecorder:
    """将广播事件带相对时间戳追加写入 replays/{session_id}.jsonl。

    用法::

        recorder = ReplayRecorder("2026-03-04T10:00:00")
        recorder.record({"type": "task_complete", ...})
        recorder.close()
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._start_time = time.time()
        path = _ensure_dir() / f"{session_id}.jsonl"
        self._file = open(path, "a", encoding="utf-8")  # noqa: WPS515
        logger.info("[replay] session=%s path=%s", session_id, path)

    def record(self, event: dict[str, Any]) -> None:
        """追加一条事件（加 replay_ts 字段，单位秒）。"""
        try:
            enriched = {**event, "replay_ts": round(time.time() - self._start_time, 3)}
            self._file.write(json.dumps(enriched, ensure_ascii=False) + "\n")
            self._file.flush()
        except Exception as e:  # noqa: BLE001
            logger.warning("[replay] record failed: %s", e)

    def close(self) -> None:
        try:
            self._file.close()
        except Exception:  # noqa: BLE001
            pass


# ── 全局单例（由 main lifespan 管理） ─────────────────────────────────────────

_recorder: ReplayRecorder | None = None


def get_recorder() -> ReplayRecorder | None:
    return _recorder


def start_session(session_id: str | None = None) -> ReplayRecorder:
    """启动新录制 session，关闭上一个（如果有）。"""
    global _recorder
    if _recorder is not None:
        _recorder.close()
    sid = session_id or datetime.now().strftime("%Y%m%dT%H%M%S")
    _recorder = ReplayRecorder(sid)
    return _recorder


def stop_session() -> None:
    """停止当前 session。"""
    global _recorder
    if _recorder is not None:
        _recorder.close()
        _recorder = None


# ── 查询接口 ──────────────────────────────────────────────────────────────────

def list_sessions() -> list[dict[str, Any]]:
    """列出所有 replay session（按修改时间倒序）。"""
    d = _ensure_dir()
    sessions = []
    for f in sorted(d.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True):
        stat = f.stat()
        sessions.append({
            "session_id": f.stem,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
        })
    return sessions


def load_session_events(session_id: str) -> list[dict[str, Any]]:
    """加载指定 session 的全部事件。"""
    path = _ensure_dir() / f"{session_id}.jsonl"
    if not path.exists():
        return []
    events: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return events

