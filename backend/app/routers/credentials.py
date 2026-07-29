from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Credential, User
from ..schemas import CredentialCreate, CredentialOut, CredentialUpdate
from ..security import encrypt_secret

router = APIRouter(prefix="/api/credentials", tags=["凭据"])


def _to_out(cred: Credential) -> CredentialOut:
    return CredentialOut(
        id=cred.id,
        name=cred.name,
        type=cred.type,
        username=cred.username or "",
        has_secret=bool(cred.secret_encrypted),
        created_at=cred.created_at,
    )


def _pick_secret(cred_type: str, password, ssh_key):
    if cred_type == "password":
        return password
    if cred_type == "key":
        return ssh_key
    return None


@router.get("", response_model=List[CredentialOut])
def list_credentials(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    creds = db.query(Credential).order_by(Credential.id).all()
    return [_to_out(c) for c in creds]


@router.post("", response_model=CredentialOut)
def create_credential(
    payload: CredentialCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.type not in ("password", "key"):
        raise HTTPException(status_code=400, detail="type 必须是 password 或 key")
    secret = _pick_secret(payload.type, payload.password, payload.ssh_key)
    cred = Credential(
        name=payload.name,
        type=payload.type,
        username=payload.username,
        secret_encrypted=encrypt_secret(secret) if secret else None,
    )
    db.add(cred)
    db.commit()
    db.refresh(cred)
    return _to_out(cred)


@router.put("/{cred_id}", response_model=CredentialOut)
def update_credential(
    cred_id: int,
    payload: CredentialUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cred = db.query(Credential).filter(Credential.id == cred_id).first()
    if cred is None:
        raise HTTPException(status_code=404, detail="凭据不存在")
    if payload.name is not None:
        cred.name = payload.name
    if payload.type is not None:
        if payload.type not in ("password", "key"):
            raise HTTPException(status_code=400, detail="type 必须是 password 或 key")
        cred.type = payload.type
    if payload.username is not None:
        cred.username = payload.username
    secret = _pick_secret(cred.type, payload.password, payload.ssh_key)
    if secret:
        cred.secret_encrypted = encrypt_secret(secret)
    db.commit()
    db.refresh(cred)
    return _to_out(cred)


@router.delete("/{cred_id}")
def delete_credential(
    cred_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cred = db.query(Credential).filter(Credential.id == cred_id).first()
    if cred is None:
        raise HTTPException(status_code=404, detail="凭据不存在")
    db.delete(cred)
    db.commit()
    return {"detail": "已删除"}
