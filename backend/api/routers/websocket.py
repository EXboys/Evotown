"""WebSocket 路由"""
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.deps import arena, manager, task_dispatcher, ws, incoming_ws
from ws_messages import StateSnapshotAgent

logger = logging.getLogger("evotown.ws")
router = APIRouter(tags=["websocket"])


def _build_snapshot_agent(rec) -> StateSnapshotAgent:
    a: StateSnapshotAgent = {
        "agent_id": rec.agent_id,
        "display_name": rec.display_name,
        "balance": rec.balance,
        "in_task": rec.in_task,
    }
    if rec.team_id:
        a["team_id"] = rec.team_id
        team = arena.get_team(rec.team_id)
        if team:
            a["team_name"] = team.name
    return a


@router.websocket("/ws")
async def websocket_endpoint(ws_conn: WebSocket):
    await manager.connect(ws_conn)
    # 新连接必须直接发送 state_snapshot，确保客户端收到 agent 列表（含队伍信息）
    snapshot_agents: list[StateSnapshotAgent] = [
        _build_snapshot_agent(rec) for rec in arena.agents.values()
    ]
    try:
        await ws_conn.send_json(ws.state_snapshot(snapshot_agents))
        # 若有队伍，立即发送 team_formed，确保前端 Phaser 显示旗帜和标签
        teams = arena.list_teams()
        if teams:
            teams_info = [
                {
                    "team_id": t.team_id,
                    "name": t.name,
                    "members": [{"agent_id": aid, "display_name": arena.get_agent(aid).display_name or aid} for aid in t.members if arena.get_agent(aid)],
                }
                for t in teams
            ]
            await ws_conn.send_json(ws.team_formed(teams_info))
    except Exception as e:
        logger.warning("Failed to send state_snapshot/team_formed to new client: %s", e)
    for t in task_dispatcher.get_available_tasks():
        try:
            await ws_conn.send_json(
                ws.task_available(
                    t["task_id"], t["task"], t["difficulty"], t["created_at"]
                )
            )
        except Exception as e:
            logger.warning("Failed to send task_available to new client: %s", e)
    try:
        while True:
            data = await ws_conn.receive_text()
            handled = await incoming_ws.dispatch(data)
            if not handled:
                try:
                    msg = json.loads(data)
                    if msg.get("type") == "ping":
                        await ws_conn.send_json(ws.pong())
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        manager.disconnect(ws_conn)
