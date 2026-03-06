"""结阵（队伍）路由 — 组队分配、救援转账、自治偏好"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.deps import arena, ws
from core.config import load_team_config
from domain.arena import EVOLUTION_FOCUS_OPTIONS

logger = logging.getLogger("evotown.routers.teams")

router = APIRouter(prefix="/teams", tags=["teams"])


# ── 请求/响应模型 ─────────────────────────────────────────────────────────────

class AssignTeamsRequest(BaseModel):
    num_teams: int = Field(default=2, ge=2, description="队伍数量（最少 2 队）")


class AgentPreferenceRequest(BaseModel):
    solo_preference: Optional[bool] = Field(
        default=None,
        description="True = 主动选择自由人（不被强制入队）；False = 愿意入队",
    )
    evolution_focus: Optional[str] = Field(
        default=None,
        description=(
            f"进化方向偏好。合法值：{list(EVOLUTION_FOCUS_OPTIONS.keys())} 或空串（无偏好）"
        ),
    )


class RescueRequest(BaseModel):
    target_id: str = Field(..., description="被救 agent 的 ID")
    amount: int = Field(..., gt=0, description="转移的军功值（> 0）")


# ── 路由实现 ──────────────────────────────────────────────────────────────────

@router.post("/assign")
async def assign_teams(body: AssignTeamsRequest):
    """将当前所有活跃 agent 随机分成 num_teams 队（结阵）。

    硬约束：
    - num_teams >= 2
    - 活跃 agent 数 >= num_teams（每队至少 1 人）
    - 全员不能同队（num_teams >= 2 已保证）
    """
    try:
        teams = arena.assign_teams(body.num_teams)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 构建 WS 广播用的 TeamInfo 列表
    teams_info = []
    for t in teams:
        members_info = []
        for aid in t.members:
            a = arena.get_agent(aid)
            members_info.append({
                "agent_id": aid,
                "display_name": a.display_name if a else aid,
            })
        teams_info.append({
            "team_id": t.team_id,
            "name": t.name,
            "members": members_info,
        })

    await ws.send_team_formed(teams_info)  # type: ignore[arg-type]
    logger.info("结阵完成：%d 队，成员分布 %s",
                len(teams), [len(t.members) for t in teams])

    return {"ok": True, "teams": [t.to_serializable() for t in teams]}


@router.get("")
async def list_teams():
    """查询当前所有队伍及成员信息"""
    teams = arena.list_teams()
    result = []
    for t in teams:
        members_info = []
        for aid in t.members:
            a = arena.get_agent(aid)
            members_info.append({
                "agent_id": aid,
                "display_name": a.display_name if a else aid,
                "balance": a.balance if a else 0,
                "in_task": a.in_task if a else False,
            })
        result.append({**t.to_serializable(), "members_detail": members_info})
    return {"teams": result, "total": len(result)}


@router.delete("")
async def dissolve_teams():
    """解散所有队伍，清空 agent.team_id"""
    arena.dissolve_teams()
    logger.info("所有队伍已解散")
    return {"ok": True, "message": "所有队伍已解散"}


@router.post("/agents/{agent_id}/rescue")
async def rescue_agent(agent_id: str, body: RescueRequest):
    """队内救援：agent_id（施救者）向 target_id（受救者）转移军功值。

    约束：
    - 双方必须在同一队伍
    - 转移量 > 0
    - 施救者余额 >= 转移量
    触发后广播 rescue_event；若受救者余额仍低于危机阈值则追加 rescue_needed。
    """
    ok, msg = arena.rescue_transfer(agent_id, body.target_id, body.amount)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)

    donor = arena.get_agent(agent_id)
    target = arena.get_agent(body.target_id)
    team = arena.get_agent_team(agent_id)

    # 持久化
    from core.deps import experiment_id
    arena.persist(experiment_id or None)

    # 广播救援事件
    await ws.send_rescue_event(
        donor_id=agent_id,
        donor_display_name=donor.display_name if donor else agent_id,
        target_id=body.target_id,
        target_display_name=target.display_name if target else body.target_id,
        amount=body.amount,
        donor_balance=donor.balance if donor else 0,
        target_balance=target.balance if target else 0,
        team_id=team.team_id if team else "",
        team_name=team.name if team else "",
    )

    # 危机预警：受救者余额仍偏低（< 30）时广播 rescue_needed
    RESCUE_THRESHOLD = 30
    if target and target.balance < RESCUE_THRESHOLD and team:
        await ws.send_rescue_needed(
            agent_id=body.target_id,
            display_name=target.display_name,
            balance=target.balance,
            team_id=team.team_id,
            team_name=team.name,
        )

    logger.info("[rescue] %s → %s 转移军功 %d；%s", agent_id, body.target_id, body.amount, msg)
    return {"ok": True, "message": msg,
            "donor_balance": donor.balance if donor else 0,
            "target_balance": target.balance if target else 0}


@router.post("/reorganize")
async def manual_reorganize():
    """手动触发一次社会重组（无需等定时器，便于测试）。

    规则同自动重组：弱队解散→流民池，强队扣维系成本，流民随机补入强队或重新组队。
    """
    teams = arena.list_teams()
    if not teams:
        raise HTTPException(status_code=400, detail="当前没有队伍，请先调用 /teams/assign 结阵")

    team_cfg = load_team_config()
    cost_stay = team_cfg["cost_stay"]
    max_team_ratio = team_cfg["max_team_ratio"]

    result = arena.reorganize_teams(cost_stay=cost_stay, max_team_ratio=max_team_ratio)

    # 持久化
    from core.deps import experiment_id
    arena.persist(experiment_id or None)

    global_count = arena.global_task_counter
    await ws.send_team_reorganized(
        survived_teams=result.survived_teams,
        dissolved_teams=result.dissolved_teams,
        dissolved_team_names=result.dissolved_team_names,
        refugees=result.refugees,
        cost_stay=result.cost_stay,
        global_task_count=global_count,
    )

    logger.info(
        "[reorganize/manual] 存活 %d 队，解散 %d 队（%s），流民 %d 人",
        len(result.survived_teams), len(result.dissolved_teams),
        "、".join(result.dissolved_team_names) or "无",
        len(result.refugees),
    )
    return {"ok": True, **result.to_dict(), "global_task_count": global_count}



@router.patch("/agents/{agent_id}/preference")
async def set_agent_preference(agent_id: str, body: AgentPreferenceRequest):
    """设置 agent 的自治偏好：solo_preference（自由人模式）和 evolution_focus（进化方向）。

    - `solo_preference=true`  → 下次结阵/重组时该 agent 不会被强制入队
    - `solo_preference=false` → 恢复普通入队资格
    - `evolution_focus`       → 设置进化方向（biases LLM prompt），空串清除偏好

    合法的 evolution_focus 值：
    """ + "\n    ".join(f"- `{k}`: {v}" for k, v in EVOLUTION_FOCUS_OPTIONS.items()) + """
    """
    a = arena.get_agent(agent_id)
    if a is None:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")

    changed: dict = {}

    if body.solo_preference is not None:
        a.solo_preference = body.solo_preference
        changed["solo_preference"] = a.solo_preference
        # 若切回普通模式且当前在队伍里，不做额外操作（下次结阵自然参与）
        # 若切为 solo 且当前在队伍里，也不强制退队（保留当前队伍直到下次重组）
        logger.info(
            "[%s] solo_preference → %s", agent_id, a.solo_preference
        )

    if body.evolution_focus is not None:
        focus = body.evolution_focus.strip()
        if focus and focus not in EVOLUTION_FOCUS_OPTIONS:
            raise HTTPException(
                status_code=400,
                detail=f"无效的 evolution_focus '{focus}'，合法值：{list(EVOLUTION_FOCUS_OPTIONS.keys())}",
            )
        a.evolution_focus = focus
        changed["evolution_focus"] = a.evolution_focus
        logger.info("[%s] evolution_focus → '%s'", agent_id, a.evolution_focus)

    if not changed:
        raise HTTPException(status_code=400, detail="请至少提供 solo_preference 或 evolution_focus 其中一个字段")

    # 持久化
    from core.deps import experiment_id
    arena.persist(experiment_id or None)

    return {
        "ok": True,
        "agent_id": agent_id,
        "display_name": a.display_name,
        "solo_preference": a.solo_preference,
        "evolution_focus": a.evolution_focus,
        "evolution_focus_desc": EVOLUTION_FOCUS_OPTIONS.get(a.evolution_focus, "无偏好"),
        "changed": changed,
    }
