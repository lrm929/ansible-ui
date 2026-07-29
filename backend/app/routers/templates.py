from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Credential, Inventory, Project, Template, User
from ..schemas import TemplateCreate, TemplateOut, TemplateUpdate

router = APIRouter(prefix="/api/templates", tags=["模板"])


def _get_template(db: Session, template_id: int) -> Template:
    tpl = db.query(Template).filter(Template.id == template_id).first()
    if tpl is None:
        raise HTTPException(status_code=404, detail="模板不存在")
    return tpl


def _check_refs(db: Session, project_id, inventory_id, credential_id):
    if project_id is not None:
        if db.query(Project).filter(Project.id == project_id).first() is None:
            raise HTTPException(status_code=400, detail="关联的项目不存在")
    if inventory_id is not None:
        if db.query(Inventory).filter(Inventory.id == inventory_id).first() is None:
            raise HTTPException(status_code=400, detail="关联的清单不存在")
    if credential_id is not None:
        if db.query(Credential).filter(Credential.id == credential_id).first() is None:
            raise HTTPException(status_code=400, detail="关联的凭据不存在")


def _to_out(tpl: Template) -> TemplateOut:
    return TemplateOut(
        id=tpl.id,
        name=tpl.name,
        project_id=tpl.project_id,
        playbook=tpl.playbook,
        inventory_id=tpl.inventory_id,
        credential_id=tpl.credential_id,
        extra_vars=tpl.extra_vars or "",
        limit=tpl.limit or "",
        tags=tpl.tags or "",
        created_at=tpl.created_at,
        project_name=tpl.project.name if tpl.project else None,
        inventory_name=tpl.inventory.name if tpl.inventory else None,
        credential_name=tpl.credential.name if tpl.credential else None,
    )


@router.get("", response_model=List[TemplateOut])
def list_templates(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    tpls = db.query(Template).order_by(Template.id).all()
    return [_to_out(t) for t in tpls]


@router.post("", response_model=TemplateOut)
def create_template(
    payload: TemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_refs(db, payload.project_id, payload.inventory_id, payload.credential_id)
    tpl = Template(
        name=payload.name,
        project_id=payload.project_id,
        playbook=payload.playbook,
        inventory_id=payload.inventory_id,
        credential_id=payload.credential_id,
        extra_vars=payload.extra_vars,
        limit=payload.limit,
        tags=payload.tags,
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)
    return _to_out(tpl)


@router.put("/{template_id}", response_model=TemplateOut)
def update_template(
    template_id: int,
    payload: TemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tpl = _get_template(db, template_id)
    _check_refs(db, payload.project_id, payload.inventory_id, payload.credential_id)
    for field in (
        "name", "project_id", "playbook", "inventory_id",
        "credential_id", "extra_vars", "limit", "tags",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(tpl, field, value)
    db.commit()
    db.refresh(tpl)
    return _to_out(tpl)


@router.delete("/{template_id}")
def delete_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tpl = _get_template(db, template_id)
    db.delete(tpl)
    db.commit()
    return {"detail": "已删除"}
