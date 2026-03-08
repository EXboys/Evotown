"""WebSocket 路由"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from core.deps import arena, manager, task_dispatcher, ws, incoming_ws
from ws_messages import StateSnapshotAgent

logger = logging.getLogger("evotown.ws")
router = APIRouter(tags=["websocket"])

# 心跳配置
HEARTBEAT_INTERVAL_SEC = 30  # 服务端发送 ping 间隔（秒）
PONG_TIMEOUT_SEC = 15  # 客户端响应 pong 超时（秒）


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

    # 心跳状态追踪
    last_pong_time = datetime.now()
    heartbeat_task: Optional[asyncio.Task] = None
    ping_timer_task: Optional[asyncio.Task] = None
    is_active = True

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

    async def send_periodic_ping():
        """定期发送 server_ping 消息"""
        nonlocal is_active
        while is_active:
            try:
                await asyncio.sleep(HEARTBEAT_INTERVAL_SEC)
                if not is_active:
                    break
                try:
                    await ws_conn.send_json(ws.server_ping())
                except Exception as e:
                    logger.warning("Failed to send server_ping: %s", e)
                    break
            except asyncio.CancelledError:
                break

    async def monitor_pong_timeout():
        """监控客户端 pong 响应超时"""
        nonlocal last_pong_time, is_active
        while is_active:
            try:
                await asyncio.sleep(PONG_TIMEOUT_SEC)
                if not is_active:
                    break
                elapsed = (datetime.now() - last_pong_time).total_seconds()
                if elapsed > PONG_TIMEOUT_SEC:
                    logger.warning(
                        "No pong received for %.1fs (timeout=%ds), closing connection",
                        elapsed, PONG_TIMEOUT_SEC
                    )
                    break
            except asyncio.CancelledError:
                break

    # 启动心跳任务
    heartbeat_task = asyncio.create_task(send_periodic_ping())
    ping_timer_task = asyncio.create_task(monitor_pong_timeout())

    try:
        while True:
            data = await ws_conn.receive_text()
            handled = await incoming_ws.dispatch(data)
            if not handled:
                try:
                    msg = json.loads(data)
                    msg_type = msg.get("type")
                    if msg_type == "ping":
                        await ws_conn.send_json(ws.pong())
                    elif msg_type == "pong":
                        # 客户端响应 pong，重置超时计时
                        last_pong_time = datetime.now()
                        logger.debug("Received pong from client")
                except json.JSONDecodeError:
                    pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.warning("WebSocket error: %s", e)
    finally:
        is_active = False
        # 取消心跳任务
        if heartbeat_task:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass
        if ping_timer_task:
            ping_timer_task.cancel()
            try:
                await ping_timer_task
            except asyncio.CancelledError:
                pass
        manager.disconnect(ws_conn)
