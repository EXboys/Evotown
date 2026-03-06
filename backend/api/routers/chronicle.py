"""战报路由 — 文言文每日战报 API

POST /chronicle/generate          手动触发（可指定日期，默认昨日）
GET  /chronicle/                  列出所有已生成战报
GET  /chronicle/{date}            获取指定日期战报（YYYY-MM-DD）
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.deps import arena, ws
from services.chronicle import generate_chronicle, list_chronicles, load_chronicle

router = APIRouter(prefix="/chronicle", tags=["chronicle"], redirect_slashes=False)


class GenerateRequest(BaseModel):
    date: str | None = None  # YYYY-MM-DD，不填默认昨日 CST


@router.post("/generate")
async def api_generate_chronicle(req: GenerateRequest | None = None):
    """手动触发文言文战报生成；可选指定 date（YYYY-MM-DD），不填则为昨日。"""
    date = req.date if req else None

    # 构建当前 agent_id → display_name 映射，让战报使用三国武将名
    agent_name_map = {aid: (rec.display_name or aid) for aid, rec in arena.agents.items()}

    async def _broadcast(data: dict) -> None:
        await ws.broadcast(data)

    record = await generate_chronicle(date, agent_name_map=agent_name_map, broadcast_fn=_broadcast)
    return {
        "ok": True,
        "date": record["date"],
        "generated_at": record["generated_at"],
        "preview": (record.get("text") or "")[:300],
    }


@router.get("")
async def api_list_chronicles():
    """列出所有已生成的战报（日期倒序），含日期、生成时间、任务数、预览前100字。"""
    return list_chronicles()


@router.get("/{date}")
async def api_get_chronicle(date: str):
    """获取指定日期（YYYY-MM-DD）的完整战报，不存在返回 404。"""
    data = load_chronicle(date)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Chronicle for '{date}' not found")
    return data

