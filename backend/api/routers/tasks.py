"""任务路由"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from core.auth import require_admin, validate_task_content
from domain.models import TaskInject, TaskBatch
from services import task_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/inject", dependencies=[Depends(require_admin)])
async def inject_task(body: TaskInject):
    # 长度 + prompt injection 双重校验（不合规则返回 400）
    validate_task_content(body.task)
    ok, err = await task_service.inject_task(body)
    if not ok:
        return JSONResponse(
            status_code=400,
            content={"ok": False, "error": err or "inject failed"},
        )
    return {"ok": True}


@router.post("/batch", dependencies=[Depends(require_admin)])
async def batch_inject(body: TaskBatch):
    # 批量注入：逐条校验所有任务内容
    for task in body.tasks:
        validate_task_content(task)
    count, err = await task_service.batch_inject(body)
    if err and count == 0:
        return {"ok": False, "count": 0, "error": err}
    return {"ok": True, "count": count}
