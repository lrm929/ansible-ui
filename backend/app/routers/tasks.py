import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..deps import get_current_user
from ..models import Task, Template, User
from ..schemas import TaskCreate, TaskOut, TaskOutputResponse
from ..security import decode_token
from ..services import executor
from ..services.ws_manager import ws_manager

router = APIRouter(prefix="/api", tags=["任务"])

FINISHED_STATUSES = ("success", "failed", "stopped")


def _get_task(db: Session, task_id: int) -> Task:
    task = db.query(Task).filter(Task.id == task_id).first()
    if task is None:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def _to_out(task: Task) -> TaskOut:
    return TaskOut(
        id=task.id,
        template_id=task.template_id,
        template_name=task.template.name if task.template else None,
        status=task.status,
        command=task.command or "",
        started_at=task.started_at,
        finished_at=task.finished_at,
        created_by=task.created_by or "",
        created_at=task.created_at,
    )


@router.post("/tasks", response_model=TaskOut)
def create_task(
    payload: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    template = db.query(Template).filter(Template.id == payload.template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="任务模板不存在")
    task = Task(
        template_id=template.id,
        status="pending",
        created_by=current_user.username,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    executor.submit_task(task.id)
    return _to_out(task)


@router.get("/tasks", response_model=List[TaskOut])
def list_tasks(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks = (
        db.query(Task)
        .order_by(Task.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return [_to_out(t) for t in tasks]


@router.get("/tasks/{task_id}", response_model=TaskOut)
def get_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _to_out(_get_task(db, task_id))


@router.post("/tasks/{task_id}/stop", response_model=TaskOut)
def stop_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task(db, task_id)
    if task.status in FINISHED_STATUSES:
        raise HTTPException(status_code=400, detail="任务已结束,无法终止")
    found = executor.stop_task(task_id)
    if not found:
        # 任务还在 pending(排队中),直接标记 stopped
        task.status = "stopped"
        task.output = (task.output or "") + "任务已被手动终止\n"
        from datetime import datetime

        task.finished_at = datetime.utcnow()
        db.commit()
        ws_manager.broadcast_end(task_id, "stopped")
    db.refresh(task)
    return _to_out(task)


@router.get("/tasks/{task_id}/output", response_model=TaskOutputResponse)
def get_task_output(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    task = _get_task(db, task_id)
    return {"output": task.output or ""}


@router.websocket("/ws/tasks/{task_id}")
async def task_ws(websocket: WebSocket, task_id: int, token: str = Query("")):
    payload = decode_token(token)
    if payload is None:
        await websocket.close(code=4401)
        return

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
    finally:
        db.close()
    if task is None:
        await websocket.close(code=4404)
        return

    if task.status in FINISHED_STATUSES:
        await websocket.accept()
        await websocket.send_text(
            json.dumps({"type": "log", "line": task.output or ""}, ensure_ascii=False)
        )
        await websocket.send_text(
            json.dumps({"type": "status", "status": task.status}, ensure_ascii=False)
        )
        await websocket.send_text(json.dumps({"type": "end"}, ensure_ascii=False))
        await websocket.close()
        return

    await ws_manager.connect(task_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(task_id, websocket)
