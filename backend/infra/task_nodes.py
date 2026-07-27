"""Unified task board nodes — sync dispatch_jobs + hosted agent runs."""
from __future__ import annotations

import json
import os
import sqlite3
import uuid
from pathlib import Path
from typing import Any

from infra import agent_dispatch, claude_agent_runs
from infra import system_config as _system_config

_backend_dir = Path(__file__).resolve().parent.parent
_evotown_data = _backend_dir.parent / "data"

_conn: sqlite3.Connection | None = None

BOARD_STATUSES = ("queued", "running", "done", "failed")
SOURCE_DISPATCH = "dispatch_job"
SOURCE_HOSTED_RUN = "hosted_run"

_DISPATCH_TO_BOARD = {
    "queued": "queued",
    "leased": "queued",
    "running": "running",
    "completed": "done",
    "failed": "failed",
    "cancelled": "failed",
}

_RUN_TO_BOARD = {
    "queued": "queued",
    "running": "running",
    "succeeded": "done",
    "failed": "failed",
    "cancelled": "failed",
}


def _data_dir() -> Path:
    default = _evotown_data if _evotown_data.is_dir() else _backend_dir / "data"
    return Path(os.environ.get("EVOTOWN_DATA_DIR", default))


def _ensure_conn() -> sqlite3.Connection:
    global _conn
    if _conn is not None:
        return _conn
    data_dir = _data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(data_dir / "task_nodes.db"), check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=10000")
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS task_nodes (
            node_id              TEXT PRIMARY KEY,
            agent_id             TEXT NOT NULL DEFAULT '',
            source_type          TEXT NOT NULL,
            source_id            TEXT NOT NULL,
            title                TEXT NOT NULL DEFAULT '',
            message              TEXT NOT NULL DEFAULT '',
            board_status         TEXT NOT NULL DEFAULT 'queued',
            source_status        TEXT NOT NULL DEFAULT '',
            depends_on_node_id   TEXT NOT NULL DEFAULT '',
            sequence             INTEGER NOT NULL DEFAULT 0,
            run_id               TEXT NOT NULL DEFAULT '',
            dispatch_job_id      TEXT NOT NULL DEFAULT '',
            payload_json         TEXT NOT NULL DEFAULT '{}',
            refs_json            TEXT NOT NULL DEFAULT '{}',
            created_at           TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at           TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at         TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS idx_task_nodes_source
            ON task_nodes(source_type, source_id);
        CREATE INDEX IF NOT EXISTS idx_task_nodes_agent_board
            ON task_nodes(agent_id, board_status, created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_task_nodes_depends
            ON task_nodes(depends_on_node_id);
        """
    )
    _conn = conn
    return conn


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _json_loads(value: str, fallback: Any) -> Any:
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _node_from_row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["payload"] = _json_loads(item.pop("payload_json", "{}"), {})
    item["refs"] = _json_loads(item.pop("refs_json", "{}"), {})
    return item


def _agent_id_from_dispatch_job(job: dict[str, Any]) -> str:
    return str(job.get("target_agent_id") or "")


def _board_status_from_dispatch(status: str) -> str:
    return _DISPATCH_TO_BOARD.get(status, "queued")


def _board_status_from_run(status: str) -> str:
    return _RUN_TO_BOARD.get(status, "queued")


def _resolve_depends_on_node_id(parent_source_id: str, *, source_type: str) -> str:
    if not parent_source_id:
        return ""
    row = _ensure_conn().execute(
        "SELECT node_id FROM task_nodes WHERE source_type=? AND source_id=?",
        (source_type, parent_source_id),
    ).fetchone()
    return str(row["node_id"]) if row else ""


def upsert_from_dispatch_job(job: dict[str, Any]) -> dict[str, Any]:
    job_id = str(job.get("job_id") or "")
    if not job_id:
        raise ValueError("job_id is required")

    agent_id = _agent_id_from_dispatch_job(job)
    refs = job.get("refs") if isinstance(job.get("refs"), dict) else {}
    parent_job_id = str(refs.get("parent_job_id") or "")
    depends_on = _resolve_depends_on_node_id(parent_job_id, source_type=SOURCE_DISPATCH) if parent_job_id else ""

    run_id = str(job.get("run_id") or "")
    source_status = str(job.get("status") or "queued")
    board_status = _board_status_from_dispatch(source_status)

    if run_id:
        run = claude_agent_runs.get_run(run_id)
        if run:
            board_status = _board_status_from_run(str(run.get("status") or source_status))
            source_status = str(run.get("status") or source_status)

    conn = _ensure_conn()
    existing = conn.execute(
        "SELECT node_id FROM task_nodes WHERE source_type=? AND source_id=?",
        (SOURCE_DISPATCH, job_id),
    ).fetchone()

    payload = job.get("payload") if isinstance(job.get("payload"), dict) else {}
    title = str(job.get("title") or "")
    message = str(job.get("message") or "")
    completed_at = job.get("completed_at")

    if existing:
        conn.execute(
            """
            UPDATE task_nodes
            SET agent_id=?, title=?, message=?, board_status=?, source_status=?,
                depends_on_node_id=?, run_id=?, dispatch_job_id=?, payload_json=?,
                refs_json=?, updated_at=datetime('now'),
                completed_at=COALESCE(?, completed_at)
            WHERE node_id=?
            """,
            (
                agent_id,
                title,
                message,
                board_status,
                source_status,
                depends_on,
                run_id,
                job_id,
                _json_dumps(payload),
                _json_dumps(refs),
                completed_at,
                existing["node_id"],
            ),
        )
        node_id = str(existing["node_id"])
    else:
        node_id = f"tn_{uuid.uuid4().hex[:20]}"
        conn.execute(
            """
            INSERT INTO task_nodes (
                node_id, agent_id, source_type, source_id, title, message,
                board_status, source_status, depends_on_node_id, run_id,
                dispatch_job_id, payload_json, refs_json, created_at, updated_at,
                completed_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), ?)
            """,
            (
                node_id,
                agent_id,
                SOURCE_DISPATCH,
                job_id,
                title,
                message,
                board_status,
                source_status,
                depends_on,
                run_id,
                job_id,
                _json_dumps(payload),
                _json_dumps(refs),
                job.get("created_at"),
                completed_at,
            ),
        )

    row = conn.execute("SELECT * FROM task_nodes WHERE node_id=?", (node_id,)).fetchone()
    assert row is not None
    return _node_from_row(row)


def upsert_from_hosted_run(run: dict[str, Any]) -> dict[str, Any] | None:
    run_id = str(run.get("run_id") or "")
    if not run_id:
        raise ValueError("run_id is required")

    signals = run.get("signals") if isinstance(run.get("signals"), dict) else {}
    dispatch_job_id = str(signals.get("dispatch_job_id") or "")
    if dispatch_job_id:
        job = agent_dispatch.get_job(dispatch_job_id)
        if job:
            return upsert_from_dispatch_job(job)
        return None

    agent_id = str(run.get("agent_id") or "")
    source_status = str(run.get("status") or "queued")
    board_status = _board_status_from_run(source_status)
    prompt = str(run.get("prompt") or "")

    conn = _ensure_conn()
    existing = conn.execute(
        "SELECT node_id FROM task_nodes WHERE source_type=? AND source_id=?",
        (SOURCE_HOSTED_RUN, run_id),
    ).fetchone()

    if existing:
        conn.execute(
            """
            UPDATE task_nodes
            SET agent_id=?, message=?, board_status=?, source_status=?,
                run_id=?, updated_at=datetime('now'),
                completed_at=COALESCE(?, completed_at)
            WHERE node_id=?
            """,
            (
                agent_id,
                prompt,
                board_status,
                source_status,
                run_id,
                run.get("completed_at"),
                existing["node_id"],
            ),
        )
        node_id = str(existing["node_id"])
    else:
        node_id = f"tn_{uuid.uuid4().hex[:20]}"
        conn.execute(
            """
            INSERT INTO task_nodes (
                node_id, agent_id, source_type, source_id, title, message,
                board_status, source_status, run_id, payload_json, refs_json,
                created_at, updated_at, completed_at
            )
            VALUES (?, ?, ?, ?, '', ?, ?, ?, ?, '{}', '{}', ?, datetime('now'), ?)
            """,
            (
                node_id,
                agent_id,
                SOURCE_HOSTED_RUN,
                run_id,
                prompt,
                board_status,
                source_status,
                run_id,
                run.get("created_at"),
                run.get("completed_at"),
            ),
        )

    row = conn.execute("SELECT * FROM task_nodes WHERE node_id=?", (node_id,)).fetchone()
    return _node_from_row(row) if row else None


def sync_recent(*, limit: int = 500) -> int:
    """Refresh task_nodes from dispatch_jobs and hosted runs. Returns upsert count."""
    count = 0
    for job in agent_dispatch.list_jobs(limit=limit):
        upsert_from_dispatch_job(job)
        count += 1

    runs_payload = claude_agent_runs.list_runs(limit=limit)
    for run in runs_payload.get("runs") or []:
        if upsert_from_hosted_run(run):
            count += 1
    return count


def list_board(
    *,
    agent_id: str | None = None,
    limit: int = 10,
) -> dict[str, Any]:
    """Return board columns plus pagination metadata.

    Fetches the newest ``limit`` nodes (across all statuses), then groups them.
    ``has_more`` is true when at least one older node exists beyond the page.
    """
    sync_recent(limit=max(limit, 200))

    where: list[str] = []
    params: list[Any] = []
    if agent_id:
        where.append("agent_id=?")
        params.append(agent_id)
    clause = "WHERE " + " AND ".join(where) if where else ""
    effective_limit = max(1, min(limit, 500))
    params.append(effective_limit + 1)

    rows = _ensure_conn().execute(
        f"""
        SELECT * FROM task_nodes
        {clause}
        ORDER BY created_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()

    has_more = len(rows) > effective_limit
    if has_more:
        rows = rows[:effective_limit]

    grouped: dict[str, list[dict[str, Any]]] = {status: [] for status in BOARD_STATUSES}
    for row in rows:
        node = _node_from_row(row)
        status = str(node.get("board_status") or "queued")
        if status not in grouped:
            status = "queued"
        grouped[status].append(node)
    return {
        "columns": grouped,
        "has_more": has_more,
        "total": len(rows),
        "limit": effective_limit,
    }


def get_node(node_id: str) -> dict[str, Any] | None:
    row = _ensure_conn().execute("SELECT * FROM task_nodes WHERE node_id=?", (node_id,)).fetchone()
    return _node_from_row(row) if row else None


# ── Maintenance mode + queued hosted runs ──────────────────────────────

def _maintenance_flag_path() -> Path:
    return _data_dir() / ".maintenance"


def is_maintenance() -> bool:
    return _maintenance_flag_path().exists()


def set_maintenance(enable: bool) -> None:
    flag = _maintenance_flag_path()
    if enable:
        flag.touch()
    else:
        flag.unlink(missing_ok=True)


def count_running() -> int:
    row = _ensure_conn().execute(
        "SELECT COUNT(*) FROM task_nodes WHERE board_status='running'",
    ).fetchone()
    return int(row[0]) if row else 0


def enqueue_hosted_run(
    *,
    agent_id: str,
    account_id: str,
    prompt: str,
    model: str = "",
    skills: list[str] | None = None,
    attachments: list[str] | None = None,
    previous_run_id: str = "",
    session_id: str = "",
    runtime_engine: str = "claude",
    tenant_id: str = "",
    team_id: str = "",
) -> dict[str, Any]:
    """Create a queued task_node for a hosted agent run (maintenance mode)."""
    node_id = f"tn_{uuid.uuid4().hex[:20]}"
    payload = {
        "account_id": account_id,
        "prompt": prompt,
        "model": model,
        "skills": skills or [],
        "attachments": attachments or [],
        "previous_run_id": previous_run_id,
        "session_id": session_id,
        "runtime_engine": runtime_engine,
        "tenant_id": tenant_id,
        "team_id": team_id,
    }
    conn = _ensure_conn()
    conn.execute(
        """
        INSERT INTO task_nodes (
            node_id, agent_id, source_type, source_id, title, message,
            board_status, source_status, payload_json, refs_json,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, '', ?, 'queued', 'queued', ?, '{}', datetime('now'), datetime('now'))
        """,
        (node_id, agent_id, SOURCE_HOSTED_RUN, node_id, prompt, _json_dumps(payload)),
    )
    row = conn.execute("SELECT * FROM task_nodes WHERE node_id=?", (node_id,)).fetchone()
    assert row is not None
    return _node_from_row(row)


def get_queued_hosted_runs(*, limit: int = 50) -> list[dict[str, Any]]:
    """Return queued hosted_run task_nodes ordered by creation time."""
    rows = _ensure_conn().execute(
        """
        SELECT * FROM task_nodes
        WHERE source_type=? AND board_status='queued'
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (SOURCE_HOSTED_RUN, limit),
    ).fetchall()
    return [_node_from_row(r) for r in rows]


def mark_node_running(node_id: str, run_id: str) -> None:
    _ensure_conn().execute(
        """
        UPDATE task_nodes
        SET board_status='running', source_status='running',
            source_id=?, run_id=?, updated_at=datetime('now')
        WHERE node_id=?
        """,
        (run_id, run_id, node_id),
    )


def mark_node_done(node_id: str, status: str = "done") -> None:
    _ensure_conn().execute(
        """
        UPDATE task_nodes
        SET board_status=?, source_status=?, completed_at=datetime('now'),
            updated_at=datetime('now')
        WHERE node_id=?
        """,
        (status, status, node_id),
    )


async def drain_queued_hosted_runs(*, max_active_per_account: int = 2) -> int:
    """Execute queued hosted runs (called on startup after deployment).
    Returns the number of runs dispatched.
    """
    from infra import claude_agent_runs as _car
    from services import claude_code_runner as _ccr
    import os as _os

    dispatched = 0
    queued = get_queued_hosted_runs(limit=100)
    for node in queued:
        p = node.get("payload") or {}
        if not isinstance(p, dict):
            p = {}
        account_id = str(p.get("account_id") or "")
        agent_id = str(node.get("agent_id") or "")

        # Check concurrency limit
        max_active = int(_system_config.get_config("EVOTOWN_CLAUDE_MAX_ACTIVE_RUNS_PER_ACCOUNT", "2") or "2")
        if max_active > 0 and _car.active_run_count(account_id) >= max_active:
            continue

        try:
            run = _car.create_run(
                agent_id=agent_id,
                account_id=account_id,
                prompt=str(p.get("prompt") or node.get("message") or ""),
                tenant_id=str(p.get("tenant_id") or ""),
                team_id=str(p.get("team_id") or ""),
                model=str(p.get("model") or ""),
                signals={
                    "workspace_name": "",
                    "selected_skills": list(p.get("skills") or []),
                    "previous_run_id": str(p.get("previous_run_id") or ""),
                    "session_id": str(p.get("session_id") or ""),
                    "attachments": list(p.get("attachments") or []),
                    "runtime_engine": str(p.get("runtime_engine") or "claude"),
                },
            )
            run_id = run["run_id"]
            mark_node_running(node["node_id"], run_id)
            _ccr.schedule_run(run_id)
            dispatched += 1
        except Exception:
            mark_node_done(node["node_id"], "failed")

    return dispatched


# ── Drain worker: 后台持续轮询排队任务 ──

import asyncio as _asyncio
import logging as _logging

_logger = _logging.getLogger("evotown.task_nodes")


async def try_drain_one() -> bool:
    """即时触发：run 完成时尝试取一个排队任务执行。返回是否派发。"""
    if is_maintenance():
        return False
    result = await drain_queued_hosted_runs(max_active_per_account=2)
    return result > 0


async def drain_hosted_runs_loop(*, poll_interval: float = 5.0) -> None:
    """后台轮询：每隔 poll_interval 秒扫描排队任务并执行。"""
    _logger.info("[drain] worker started — poll_interval=%.1fs", poll_interval)
    try:
        while True:
            try:
                dispatched = await drain_queued_hosted_runs(max_active_per_account=2)
                if dispatched:
                    _logger.info("[drain] dispatched %d queued runs", dispatched)
            except Exception as exc:
                _logger.exception("[drain] loop error: %s", exc)
            await _asyncio.sleep(poll_interval)
    except _asyncio.CancelledError:
        pass


def recover_zombie_running_runs() -> int:
    """启动恢复：将意外中断的 running 任务重置为 queued 以便 drain 重新执行。

    覆盖两个来源：
    1. task_nodes 中 board_status='running' 的记录（排队路径）
    2. claude_agent_runs 中 status='running' 但无 task_node 的记录（直接执行路径）

    返回恢复数量。
    """
    from infra import claude_agent_runs as _car
    conn = _ensure_conn()
    recovered = 0

    # ── 1. 扫描 task_nodes 中的 running 僵尸 ──
    rows = conn.execute(
        "SELECT * FROM task_nodes WHERE board_status='running' AND source_type=?",
        (SOURCE_HOSTED_RUN,),
    ).fetchall()
    for row in rows:
        node = _node_from_row(row)
        run_id = str(node.get("run_id") or "")
        if not run_id:
            conn.execute(
                "UPDATE task_nodes SET board_status='queued', source_status='queued', updated_at=datetime('now') WHERE node_id=?",
                (node["node_id"],),
            )
            recovered += 1
            continue
        run = _car.get_run(run_id)
        if run and run.get("status") == "running":
            _car.update_run_status(run_id, status="failed", error="interrupted by restart")
            conn.execute(
                "UPDATE task_nodes SET board_status='queued', source_status='queued', source_id=?, run_id='', updated_at=datetime('now') WHERE node_id=?",
                (node["node_id"], node["node_id"]),
            )
            recovered += 1

    # ── 2. 扫描 claude_agent_runs 中 running 但无 task_node 的记录 ──
    all_runs = _car.list_runs(limit=500)
    for run in all_runs.get("runs") or []:
        if run.get("status") != "running":
            continue
        rid = run["run_id"]
        existing = conn.execute(
            "SELECT 1 FROM task_nodes WHERE source_type=? AND source_id=?",
            (SOURCE_HOSTED_RUN, rid),
        ).fetchone()
        if existing:
            continue  # 已有 task_node，由步骤 1 处理
        # 无 task_node → 标记 run failed，创建 task_node 排队
        _car.update_run_status(rid, status="failed", error="interrupted by restart")
        node_id = f"tn_{uuid.uuid4().hex[:20]}"
        conn.execute(
            "INSERT INTO task_nodes (node_id, agent_id, source_type, source_id, title, message,"
            " board_status, source_status, run_id, payload_json, refs_json, created_at, updated_at)"
            " VALUES (?,?,?,?,'',?,'queued','queued','','{}','{}',datetime('now'),datetime('now'))",
            (node_id, run.get("agent_id",""), SOURCE_HOSTED_RUN, node_id, run.get("prompt","")),
        )
        recovered += 1

    if recovered:
        _logger.info("[recover] reset %d zombie running runs to queued", recovered)
    return recovered
