from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from ..database import SessionLocal
from ..models import Schedule, Task
from . import executor

scheduler = BackgroundScheduler()

_JOB_PREFIX = "schedule_"


def _job_id(schedule_id: int) -> str:
    return "{}{}".format(_JOB_PREFIX, schedule_id)


def _run_schedule(schedule_id: int):
    """cron 到点触发:新建 Task 并交给执行器。"""
    db = SessionLocal()
    try:
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()
        if schedule is None or not schedule.enabled:
            return
        task = Task(
            template_id=schedule.template_id,
            status="pending",
            created_by="scheduler",
        )
        db.add(task)
        schedule.last_run_at = datetime.utcnow()
        db.commit()
        db.refresh(task)
        executor.submit_task(task.id)
    finally:
        db.close()


def add_job(schedule_id: int, cron: str):
    trigger = CronTrigger.from_crontab(cron)
    scheduler.add_job(
        _run_schedule,
        trigger=trigger,
        args=[schedule_id],
        id=_job_id(schedule_id),
        replace_existing=True,
    )


def remove_job(schedule_id: int):
    job = scheduler.get_job(_job_id(schedule_id))
    if job is not None:
        scheduler.remove_job(_job_id(schedule_id))


def validate_cron(cron: str) -> bool:
    try:
        CronTrigger.from_crontab(cron)
        return True
    except (ValueError, TypeError):
        return False


def start_scheduler():
    """启动调度器并从数据库加载所有启用的定时任务。"""
    db = SessionLocal()
    try:
        for schedule in db.query(Schedule).filter(Schedule.enabled.is_(True)).all():
            try:
                add_job(schedule.id, schedule.cron)
            except (ValueError, TypeError):
                pass
    finally:
        db.close()
    if not scheduler.running:
        scheduler.start()


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
