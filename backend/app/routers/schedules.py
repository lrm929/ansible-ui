from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Schedule, Template, User
from ..schemas import ScheduleCreate, ScheduleOut, ScheduleUpdate
from ..services import scheduler as scheduler_service

router = APIRouter(prefix="/api/schedules", tags=["定时任务"])


def _get_schedule(db: Session, schedule_id: int) -> Schedule:
    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
    if schedule is None:
        raise HTTPException(status_code=404, detail="定时任务不存在")
    return schedule


def _to_out(schedule: Schedule) -> ScheduleOut:
    return ScheduleOut(
        id=schedule.id,
        template_id=schedule.template_id,
        template_name=schedule.template.name if schedule.template else None,
        cron=schedule.cron,
        enabled=schedule.enabled,
        last_run_at=schedule.last_run_at,
        created_at=schedule.created_at,
    )


@router.get("", response_model=List[ScheduleOut])
def list_schedules(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    schedules = db.query(Schedule).order_by(Schedule.id).all()
    return [_to_out(s) for s in schedules]


@router.post("", response_model=ScheduleOut)
def create_schedule(
    payload: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if db.query(Template).filter(Template.id == payload.template_id).first() is None:
        raise HTTPException(status_code=400, detail="关联的任务模板不存在")
    if not scheduler_service.validate_cron(payload.cron):
        raise HTTPException(status_code=400, detail="cron 表达式不合法,需要 5 段标准 cron")
    schedule = Schedule(
        template_id=payload.template_id, cron=payload.cron, enabled=payload.enabled
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    if schedule.enabled:
        scheduler_service.add_job(schedule.id, schedule.cron)
    return _to_out(schedule)


@router.put("/{schedule_id}", response_model=ScheduleOut)
def update_schedule(
    schedule_id: int,
    payload: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = _get_schedule(db, schedule_id)
    if payload.template_id is not None:
        if db.query(Template).filter(Template.id == payload.template_id).first() is None:
            raise HTTPException(status_code=400, detail="关联的任务模板不存在")
        schedule.template_id = payload.template_id
    if payload.cron is not None:
        if not scheduler_service.validate_cron(payload.cron):
            raise HTTPException(status_code=400, detail="cron 表达式不合法,需要 5 段标准 cron")
        schedule.cron = payload.cron
    if payload.enabled is not None:
        schedule.enabled = payload.enabled
    db.commit()
    db.refresh(schedule)
    if schedule.enabled:
        scheduler_service.add_job(schedule.id, schedule.cron)
    else:
        scheduler_service.remove_job(schedule.id)
    return _to_out(schedule)


@router.delete("/{schedule_id}")
def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = _get_schedule(db, schedule_id)
    scheduler_service.remove_job(schedule.id)
    db.delete(schedule)
    db.commit()
    return {"detail": "已删除"}


@router.post("/{schedule_id}/toggle", response_model=ScheduleOut)
def toggle_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    schedule = _get_schedule(db, schedule_id)
    schedule.enabled = not schedule.enabled
    db.commit()
    db.refresh(schedule)
    if schedule.enabled:
        scheduler_service.add_job(schedule.id, schedule.cron)
    else:
        scheduler_service.remove_job(schedule.id)
    return _to_out(schedule)
