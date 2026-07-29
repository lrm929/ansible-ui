from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import WebhookConfig
from ..services import notifier

router = APIRouter(prefix="/api/settings", tags=["通知设置"])


@router.get("/webhook", response_model=WebhookConfig)
def get_webhook(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return WebhookConfig(**notifier.get_webhook_config(db))


@router.put("/webhook", response_model=WebhookConfig)
def save_webhook(
    payload: WebhookConfig,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notifier.save_webhook_config(db, payload.model_dump())
    return WebhookConfig(**notifier.get_webhook_config(db))


@router.post("/webhook/test")
def test_webhook(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    cfg = notifier.get_webhook_config(db)
    if not cfg["webhook_url"]:
        raise HTTPException(status_code=400, detail="尚未配置 Webhook 地址,请先保存")
    content = "**Ansible 任务通知**\n> 这是一条测试消息,企业微信 Webhook 配置成功。"
    ok, err = notifier.send_wecom_markdown(cfg["webhook_url"], content)
    if not ok:
        raise HTTPException(status_code=502, detail=err)
    return {"detail": "测试消息已发送"}
