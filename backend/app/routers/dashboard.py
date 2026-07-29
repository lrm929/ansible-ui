from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Host, Inventory, Project, Task, Template, User

router = APIRouter(prefix="/api/dashboard", tags=["仪表盘"])


@router.get("")
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tasks_total = db.query(func.count(Task.id)).scalar() or 0
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    tasks_today = (
        db.query(func.count(Task.id)).filter(Task.created_at >= today_start).scalar() or 0
    )

    status_stats = {}
    for status, count in (
        db.query(Task.status, func.count(Task.id)).group_by(Task.status).all()
    ):
        status_stats[status] = count

    recent = db.query(Task).order_by(Task.id.desc()).limit(10).all()
    template_names = {
        t.id: t.name for t in db.query(Template.id, Template.name).all()
    }
    recent_tasks = [
        {
            "id": t.id,
            "template_id": t.template_id,
            "template_name": template_names.get(t.template_id),
            "status": t.status,
            "command": t.command,
            "started_at": t.started_at,
            "finished_at": t.finished_at,
            "created_by": t.created_by,
            "created_at": t.created_at,
        }
        for t in recent
    ]

    return {
        "hosts": db.query(func.count(Host.id)).scalar() or 0,
        "inventories": db.query(func.count(Inventory.id)).scalar() or 0,
        "projects": db.query(func.count(Project.id)).scalar() or 0,
        "templates": db.query(func.count(Template.id)).scalar() or 0,
        "tasks_total": tasks_total,
        "tasks_today": tasks_today,
        "recent_tasks": recent_tasks,
        "status_stats": status_stats,
    }
