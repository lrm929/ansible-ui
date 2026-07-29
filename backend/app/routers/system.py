import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..config import DATA_DIR
from ..database import get_db
from ..deps import get_current_user
from ..models import Setting, User
from ..schemas import SiteInfo

router = APIRouter(prefix="/api/system", tags=["系统信息"])

DEFAULT_SITE_NAME = "Ansible 运维管理平台"
_BG_CONTENT_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
_BG_EXTS = (".jpg", ".png", ".webp")
_MAX_BG_SIZE = 2 * 1024 * 1024  # 2MB


def _get_site_name(db: Session) -> str:
    row = db.query(Setting).filter(Setting.key == "site_name").first()
    if row is None or not row.value.strip():
        return DEFAULT_SITE_NAME
    return row.value


def _find_login_bg():
    for ext in _BG_EXTS:
        path = os.path.join(DATA_DIR, "login_bg" + ext)
        if os.path.isfile(path):
            return path
    return None


@router.get("/info")
def get_info(db: Session = Depends(get_db)):
    """公开接口(登录页要用),不加认证依赖。"""
    return {"site_name": _get_site_name(db), "has_login_bg": _find_login_bg() is not None}


@router.put("/info")
def save_info(
    payload: SiteInfo,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    name = payload.site_name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="系统名称不能为空")
    row = db.query(Setting).filter(Setting.key == "site_name").first()
    if row is None:
        db.add(Setting(key="site_name", value=name))
    else:
        row.value = name
    db.commit()
    return {"site_name": name, "has_login_bg": _find_login_bg() is not None}


@router.post("/login-bg")
def upload_login_bg(
    file: UploadFile, current_user: User = Depends(get_current_user)
):
    ext = _BG_CONTENT_TYPES.get(file.content_type or "")
    if ext is None:
        raise HTTPException(status_code=400, detail="仅支持 jpg / png / webp 图片")
    data = file.file.read()
    if len(data) > _MAX_BG_SIZE:
        raise HTTPException(status_code=400, detail="图片大小不能超过 2MB")
    # 先删旧的其它扩展名文件
    for e in _BG_EXTS:
        old = os.path.join(DATA_DIR, "login_bg" + e)
        if os.path.isfile(old):
            os.remove(old)
    with open(os.path.join(DATA_DIR, "login_bg" + ext), "wb") as f:
        f.write(data)
    return {"detail": "已更新"}


@router.get("/login-bg")
def get_login_bg():
    """公开接口(登录页要用)。"""
    path = _find_login_bg()
    if path is None:
        raise HTTPException(status_code=404, detail="未设置登录背景")
    return FileResponse(path)


@router.delete("/login-bg")
def delete_login_bg(current_user: User = Depends(get_current_user)):
    path = _find_login_bg()
    if path is None:
        raise HTTPException(status_code=404, detail="未设置登录背景")
    os.remove(path)
    return {"detail": "已删除"}
