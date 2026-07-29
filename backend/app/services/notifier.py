import json
import logging
import urllib.request
from datetime import datetime

from ..database import SessionLocal
from ..models import Setting, Task

logger = logging.getLogger(__name__)

# Setting 表中的键及缺省值(布尔统一存 "true"/"false" 字符串)
_DEFAULTS = {
    "webhook_url": "",
    "enabled": "false",
    "notify_on_success": "true",
    "notify_on_failure": "true",
}


def get_webhook_config(db) -> dict:
    """从 Setting 表读出 webhook 配置,缺失的键用缺省值。"""
    stored = {row.key: row.value for row in db.query(Setting).all()}
    merged = {key: stored.get(key, default) for key, default in _DEFAULTS.items()}
    return {
        "webhook_url": merged["webhook_url"],
        "enabled": merged["enabled"] == "true",
        "notify_on_success": merged["notify_on_success"] == "true",
        "notify_on_failure": merged["notify_on_failure"] == "true",
    }


def save_webhook_config(db, cfg: dict):
    values = {
        "webhook_url": cfg.get("webhook_url", "") or "",
        "enabled": _bool_str(cfg.get("enabled", False)),
        "notify_on_success": _bool_str(cfg.get("notify_on_success", True)),
        "notify_on_failure": _bool_str(cfg.get("notify_on_failure", True)),
    }
    for key, value in values.items():
        row = db.query(Setting).filter(Setting.key == key).first()
        if row is None:
            db.add(Setting(key=key, value=value))
        else:
            row.value = value
    db.commit()


def _bool_str(v) -> str:
    return "true" if v else "false"


def send_wecom_markdown(url: str, content: str):
    """向企业微信群机器人 webhook POST markdown 消息,返回 (ok, err_msg)。"""
    payload = json.dumps(
        {"msgtype": "markdown", "markdown": {"content": content}},
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            body = resp.read().decode("utf-8", "replace")
    except Exception as exc:
        return False, "Webhook 请求失败: {}".format(exc)
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return False, "Webhook 响应不是合法 JSON: {}".format(body[:200])
    if data.get("errcode") == 0:
        return True, ""
    return False, "企业微信返回错误: {}".format(body[:300])


def notify_task_finished(task_id: int):
    """任务进入终态后按需发送企业微信通知。任何失败只记录日志,绝不抛出。"""
    try:
        db = SessionLocal()
        try:
            cfg = get_webhook_config(db)
            if not cfg["enabled"] or not cfg["webhook_url"]:
                return
            task = db.query(Task).filter(Task.id == task_id).first()
            if task is None or task.status not in ("success", "failed", "stopped"):
                return
            if task.status == "success" and not cfg["notify_on_success"]:
                return
            # stopped 视为非成功,走失败开关
            if task.status in ("failed", "stopped") and not cfg["notify_on_failure"]:
                return
            content = _build_task_message(task)
        finally:
            db.close()
        ok, err = send_wecom_markdown(cfg["webhook_url"], content)
        if not ok:
            logger.warning("任务 %s 企业微信通知发送失败: %s", task_id, err)
    except Exception:
        logger.exception("任务 %s 企业微信通知发送异常", task_id)


def _build_task_message(task: Task) -> str:
    template_name = task.template.name if task.template else "-"
    # 企微 markdown 仅支持 info(绿)/comment(灰)/warning(橙红) 三种字体颜色,
    # 无纯红色,失败用 warning(橙红)代替,停止也用 warning(橙)
    status_map = {
        "success": '<font color="info">成功</font>',
        "failed": '<font color="warning">失败</font>',
        "stopped": '<font color="warning">已停止</font>',
    }
    status_html = status_map.get(task.status, task.status)
    started_str = (
        task.started_at.strftime("%Y-%m-%d %H:%M:%S") if task.started_at else "-"
    )
    lines = [
        "**Ansible 任务通知**",
        "> 任务模板:{}".format(template_name),
        "> 任务 ID:{}".format(task.id),
        "> 状态:{}".format(status_html),
        "> 执行人:{}".format(task.created_by or "-"),
        "> 开始时间:{}".format(started_str),
        "> 耗时:{}".format(_fmt_duration(task)),
    ]
    if task.status in ("failed", "stopped"):
        tail = [l for l in (task.output or "").splitlines() if l.strip()][-5:]
        if tail:
            lines.append("> 日志末尾:")
            for line in tail:
                lines.append("> {}".format(line))
    return "\n".join(lines)


def _fmt_duration(task: Task) -> str:
    if not task.started_at or not task.finished_at:
        return "-"
    seconds = int((task.finished_at - task.started_at).total_seconds())
    if seconds < 0:
        return "-"
    if seconds < 60:
        return "{}秒".format(seconds)
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return "{}分{}秒".format(minutes, sec)
    hours, minutes = divmod(minutes, 60)
    return "{}小时{}分{}秒".format(hours, minutes, sec)
