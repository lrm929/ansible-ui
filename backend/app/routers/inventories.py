import json
import urllib.request
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Credential, Host, Inventory, User
from ..schemas import (
    HostCreate,
    HostImportResult,
    HostOut,
    HostUpdate,
    InventoryCreate,
    InventoryOut,
    InventoryUpdate,
)
from ..security import encrypt_secret
from ..services import host_import

router = APIRouter(prefix="/api", tags=["清单"])


def _to_out(inv: Inventory) -> InventoryOut:
    return InventoryOut(
        id=inv.id,
        name=inv.name,
        description=inv.description or "",
        host_count=len(inv.hosts),
        source_url=inv.source_url,
        last_sync_at=inv.last_sync_at,
        sync_status=inv.sync_status or "never",
        sync_message=inv.sync_message or "",
        os_type=inv.os_type or "linux",
        exclude_rules=inv.exclude_rules or "",
        credential_id=inv.credential_id,
        credential_name=inv.credential.name if inv.credential else None,
        default_username=inv.default_username or "",
        has_default_password=bool(inv.default_password_encrypted),
        default_port=inv.default_port,
        created_at=inv.created_at,
    )


def _check_credential(db: Session, credential_id):
    if credential_id:
        if db.query(Credential).filter(Credential.id == credential_id).first() is None:
            raise HTTPException(status_code=400, detail="关联的凭据不存在")


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
    if payload.os_type not in ("linux", "windows"):
        raise HTTPException(status_code=400, detail="os_type 只能是 linux 或 windows")
    _check_credential(db, payload.credential_id)
    inv = Inventory(
        name=payload.name,
        description=payload.description,
        source_url=payload.source_url or None,
        os_type=payload.os_type,
        exclude_rules=payload.exclude_rules,
        credential_id=payload.credential_id or None,
        default_username=payload.default_username,
        default_port=payload.default_port,
    )
    if payload.default_password:
        inv.default_password_encrypted = encrypt_secret(payload.default_password)
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
    if payload.source_url is not None:
        inv.source_url = payload.source_url or None
    if payload.os_type is not None:
        if payload.os_type not in ("linux", "windows"):
            raise HTTPException(status_code=400, detail="os_type 只能是 linux 或 windows")
        inv.os_type = payload.os_type
    if payload.exclude_rules is not None:
        inv.exclude_rules = payload.exclude_rules
    if payload.credential_id is not None:
        _check_credential(db, payload.credential_id)
        inv.credential_id = payload.credential_id or None
    if payload.default_username is not None:
        inv.default_username = payload.default_username
    if payload.default_password:
        inv.default_password_encrypted = encrypt_secret(payload.default_password)
    if payload.default_port is not None:
        inv.default_port = payload.default_port or None
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


@router.post("/inventories/{inv_id}/hosts/import", response_model=HostImportResult)
def import_hosts(
    inv_id: int,
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = _get_inventory(db, inv_id)
    data = file.file.read()
    text = host_import.decode_csv_bytes(data)
    if (file.filename or "").lower().endswith(".txt"):
        rows, errors = host_import.parse_assets_txt(text)
    else:
        rows, errors = host_import.parse_csv(text)
    if not rows and not errors:
        raise HTTPException(status_code=400, detail="CSV 内容为空或无法解析")
    rows, excluded = host_import.apply_exclude_rules(rows, inv.exclude_rules)
    added, updated = host_import.upsert_hosts(db, inv_id, rows)
    return HostImportResult(added=added, updated=updated, excluded=excluded, errors=errors)


@router.post("/inventories/{inv_id}/sync", response_model=HostImportResult)
def sync_hosts(
    inv_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inv = _get_inventory(db, inv_id)
    if not inv.source_url:
        raise HTTPException(status_code=400, detail="该清单未配置自动拉取地址(source_url)")
    try:
        req = urllib.request.Request(
            inv.source_url, headers={"User-Agent": "ansible-ui"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            content_type = resp.headers.get("Content-Type", "")
            body = resp.read()
    except Exception as exc:
        _sync_failed(db, inv, "拉取失败: {}".format(exc))
    try:
        rows, errors = _parse_sync_body(body, content_type)
    except Exception as exc:
        _sync_failed(db, inv, "解析失败: {}".format(exc))
    # 安全保护:解析 0 条且有错误(疑似源数据异常),不删任何主机,防止源故障清空清单
    if not rows and errors:
        _sync_failed(
            db,
            inv,
            "源数据疑似异常: 解析 0 条且有 {} 条错误,已中止同步".format(len(errors)),
        )
    rows, excluded = host_import.apply_exclude_rules(rows, inv.exclude_rules)
    added, updated = host_import.upsert_hosts(db, inv_id, rows)
    # 全量替换:删除清单中不在本次拉取结果里的主机(rows 为 0 且源合法为空时清空)
    keep = {r["hostname"] for r in rows}
    if keep:
        stale = (
            db.query(Host)
            .filter(Host.inventory_id == inv_id, ~Host.hostname.in_(keep))
            .all()
        )
    else:
        stale = db.query(Host).filter(Host.inventory_id == inv_id).all()
    removed = len(stale)
    for host in stale:
        db.delete(host)
    inv.sync_status = "ok"
    inv.sync_message = "新增 {} 台,更新 {} 台,删除 {} 台".format(added, updated, removed)
    if excluded:
        inv.sync_message += ",排除 {} 台".format(excluded)
    inv.last_sync_at = datetime.utcnow()
    db.commit()
    return HostImportResult(
        added=added, updated=updated, removed=removed, excluded=excluded, errors=errors
    )


def _sync_failed(db: Session, inv: Inventory, message: str):
    inv.sync_status = "error"
    inv.sync_message = message
    inv.last_sync_at = datetime.utcnow()
    db.commit()
    raise HTTPException(status_code=502, detail=message)


def _parse_sync_body(body: bytes, content_type: str):
    """识别顺序:lstrip 后 [ 开头 -> JSON;含 | -> LoadGameData 资产接口;否则 CSV。"""
    text = host_import.decode_csv_bytes(body)
    stripped = text.lstrip()
    if "json" in content_type.lower() or stripped.startswith("["):
        data = json.loads(stripped)
        if not isinstance(data, list):
            raise ValueError("JSON 内容不是数组")
        rows = []
        errors = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                errors.append("第{}项: 不是对象".format(i + 1))
                continue
            hostname = str(item.get("hostname") or "").strip()
            if not hostname:
                errors.append("第{}项: 主机名为空".format(i + 1))
                continue
            rows.append(
                {
                    "hostname": hostname,
                    "port": host_import._parse_port(item.get("port", 22)),
                    "group_name": str(item.get("group_name") or ""),
                    "vars": str(item.get("vars") or ""),
                    "comment": str(item.get("comment") or ""),
                }
            )
        return rows, errors
    if "|" in text:
        return host_import.parse_gamedata(text)
    return host_import.parse_csv(text)
