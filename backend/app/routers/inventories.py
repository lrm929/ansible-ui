from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Host, Inventory, User
from ..schemas import (
    HostCreate,
    HostOut,
    HostUpdate,
    InventoryCreate,
    InventoryOut,
    InventoryUpdate,
)

router = APIRouter(prefix="/api", tags=["清单"])


def _to_out(inv: Inventory) -> InventoryOut:
    return InventoryOut(
        id=inv.id,
        name=inv.name,
        description=inv.description or "",
        host_count=len(inv.hosts),
        created_at=inv.created_at,
    )


def _get_inventory(db: Session, inv_id: int) -> Inventory:
    inv = db.query(Inventory).filter(Inventory.id == inv_id).first()
    if inv is None:
        raise HTTPException(status_code=404, detail="清单不存在")
    return inv


@router.get("/inventories", response_model=List[InventoryOut])
def list_inventories(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    invs = db.query(Inventory).order_by(Inventory.id).all()
    return [_to_out(i) for i in invs]


@router.post("/inventories", response_model=InventoryOut)
def create_inventory(
    payload: InventoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = Inventory(name=payload.name, description=payload.description)
    db.add(inv)
    db.commit()
    db.refresh(inv)
    return _to_out(inv)


@router.put("/inventories/{inv_id}", response_model=InventoryOut)
def update_inventory(
    inv_id: int,
    payload: InventoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = _get_inventory(db, inv_id)
    if payload.name is not None:
        inv.name = payload.name
    if payload.description is not None:
        inv.description = payload.description
    db.commit()
    db.refresh(inv)
    return _to_out(inv)


@router.delete("/inventories/{inv_id}")
def delete_inventory(
    inv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = _get_inventory(db, inv_id)
    db.delete(inv)
    db.commit()
    return {"detail": "已删除"}


@router.get("/inventories/{inv_id}/hosts", response_model=List[HostOut])
def list_hosts(
    inv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_inventory(db, inv_id)
    hosts = db.query(Host).filter(Host.inventory_id == inv_id).order_by(Host.id).all()
    return hosts


@router.post("/inventories/{inv_id}/hosts", response_model=HostOut)
def create_host(
    inv_id: int,
    payload: HostCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_inventory(db, inv_id)
    host = Host(
        inventory_id=inv_id,
        hostname=payload.hostname,
        port=payload.port,
        group_name=payload.group_name,
        vars=payload.vars,
        comment=payload.comment,
    )
    db.add(host)
    db.commit()
    db.refresh(host)
    return host


@router.put("/hosts/{host_id}", response_model=HostOut)
def update_host(
    host_id: int,
    payload: HostUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = db.query(Host).filter(Host.id == host_id).first()
    if host is None:
        raise HTTPException(status_code=404, detail="主机不存在")
    for field in ("hostname", "port", "group_name", "vars", "comment"):
        value = getattr(payload, field)
        if value is not None:
            setattr(host, field, value)
    db.commit()
    db.refresh(host)
    return host


@router.delete("/hosts/{host_id}")
def delete_host(
    host_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    host = db.query(Host).filter(Host.id == host_id).first()
    if host is None:
        raise HTTPException(status_code=404, detail="主机不存在")
    db.delete(host)
    db.commit()
    return {"detail": "已删除"}
