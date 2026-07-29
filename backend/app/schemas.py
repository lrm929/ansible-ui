from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------- 认证 ----------
class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


class PasswordChangeRequest(BaseModel):
    old_password: str
    new_password: str


# ---------- 凭据 ----------
class CredentialBase(BaseModel):
    name: str
    type: str = "password"  # password | key
    username: str = ""


class CredentialCreate(CredentialBase):
    password: Optional[str] = None
    ssh_key: Optional[str] = None


class CredentialUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    ssh_key: Optional[str] = None


class CredentialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    type: str
    username: str
    has_secret: bool = False
    created_at: datetime


# ---------- 清单 / 主机 ----------
class InventoryCreate(BaseModel):
    name: str
    description: str = ""
    source_url: Optional[str] = None
    os_type: str = "linux"  # linux | windows
    exclude_rules: str = ""
    credential_id: Optional[int] = None
    default_username: str = ""
    default_password: Optional[str] = None
    default_port: Optional[int] = None


class InventoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    source_url: Optional[str] = None
    os_type: Optional[str] = None
    exclude_rules: Optional[str] = None
    credential_id: Optional[int] = None
    default_username: Optional[str] = None
    default_password: Optional[str] = None  # 不传/空表示不修改
    default_port: Optional[int] = None


class InventoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str
    host_count: int = 0
    source_url: Optional[str] = None
    last_sync_at: Optional[datetime] = None
    sync_status: str = "never"
    sync_message: str = ""
    os_type: str = "linux"
    exclude_rules: str = ""
    credential_id: Optional[int] = None
    credential_name: Optional[str] = None
    default_username: str = ""
    has_default_password: bool = False
    default_port: Optional[int] = None
    created_at: datetime


class HostImportResult(BaseModel):
    added: int
    updated: int
    excluded: int = 0
    errors: list = []


class HostCreate(BaseModel):
    hostname: str
    port: int = 22
    group_name: str = ""
    vars: str = ""
    comment: str = ""


class HostUpdate(BaseModel):
    hostname: Optional[str] = None
    port: Optional[int] = None
    group_name: Optional[str] = None
    vars: Optional[str] = None
    comment: Optional[str] = None


class HostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    inventory_id: int
    hostname: str
    port: int
    group_name: str
    vars: str
    comment: str


# ---------- 项目 ----------
class ProjectCreate(BaseModel):
    name: str
    source_type: str = "local"  # local | git
    local_path: Optional[str] = None
    git_url: Optional[str] = None
    git_branch: str = "main"


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    source_type: Optional[str] = None
    local_path: Optional[str] = None
    git_url: Optional[str] = None
    git_branch: Optional[str] = None


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    source_type: str
    local_path: Optional[str] = None
    git_url: Optional[str] = None
    git_branch: str = "main"
    last_sync_at: Optional[datetime] = None
    sync_status: str = "never"
    sync_message: str = ""


class PlaybooksResponse(BaseModel):
    playbooks: list


# ---------- 模板 ----------
class TemplateCreate(BaseModel):
    name: str
    project_id: int
    playbook: str
    inventory_id: int
    credential_id: Optional[int] = None
    extra_vars: str = ""
    limit: str = ""
    tags: str = ""


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    project_id: Optional[int] = None
    playbook: Optional[str] = None
    inventory_id: Optional[int] = None
    credential_id: Optional[int] = None
    extra_vars: Optional[str] = None
    limit: Optional[str] = None
    tags: Optional[str] = None


class TemplateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    project_id: int
    playbook: str
    inventory_id: int
    credential_id: Optional[int] = None
    extra_vars: str = ""
    limit: str = ""
    tags: str = ""
    created_at: datetime
    project_name: Optional[str] = None
    inventory_name: Optional[str] = None
    credential_name: Optional[str] = None


# ---------- 任务 ----------
class TaskCreate(BaseModel):
    template_id: int


class TaskOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: Optional[int] = None
    template_name: Optional[str] = None
    status: str
    command: str = ""
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    created_by: str = ""
    created_at: datetime


class TaskOutputResponse(BaseModel):
    output: str


# ---------- 定时任务 ----------
class ScheduleCreate(BaseModel):
    template_id: int
    cron: str = Field(..., description="5 段标准 cron 表达式")
    enabled: bool = True


class ScheduleUpdate(BaseModel):
    template_id: Optional[int] = None
    cron: Optional[str] = None
    enabled: Optional[bool] = None


class ScheduleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    template_id: int
    template_name: Optional[str] = None
    cron: str
    enabled: bool
    last_run_at: Optional[datetime] = None
    created_at: datetime


# ---------- 通知设置 ----------
class WebhookConfig(BaseModel):
    webhook_url: str = ""
    enabled: bool = False
    notify_on_success: bool = True
    notify_on_failure: bool = True


# ---------- 仪表盘 ----------
class DashboardOut(BaseModel):
    hosts: int
    inventories: int
    projects: int
    templates: int
    tasks_total: int
    tasks_today: int
    recent_tasks: list
    status_stats: dict
