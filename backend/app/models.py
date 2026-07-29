from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    role = Column(String(32), default="admin", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class Credential(Base):
    __tablename__ = "credentials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    type = Column(String(16), nullable=False)  # password | key
    username = Column(String(128), default="")
    secret_encrypted = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Inventory(Base):
    __tablename__ = "inventories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    description = Column(String(512), default="")
    source_url = Column(String(512), nullable=True)  # HTTP API 自动拉取地址
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String(16), default="never")  # never | ok | error
    sync_message = Column(Text, default="")
    os_type = Column(String(16), default="linux")  # linux | windows
    exclude_rules = Column(Text, default="")  # 每行一条,主机名/分组包含即排除
    credential_id = Column(Integer, ForeignKey("credentials.id"), nullable=True)
    default_username = Column(String(128), default="")
    default_password_encrypted = Column(Text, nullable=True)  # Fernet 加密,永不回传
    default_port = Column(Integer, nullable=True)  # 可空:linux 22 / windows 5985
    created_at = Column(DateTime, default=datetime.utcnow)

    hosts = relationship("Host", back_populates="inventory", cascade="all, delete-orphan")
    credential = relationship("Credential")


class Host(Base):
    __tablename__ = "hosts"

    id = Column(Integer, primary_key=True, index=True)
    inventory_id = Column(Integer, ForeignKey("inventories.id"), nullable=False)
    hostname = Column(String(256), nullable=False)
    port = Column(Integer, default=22)
    group_name = Column(String(128), default="")
    vars = Column(String(512), default="")
    comment = Column(String(512), default="")

    inventory = relationship("Inventory", back_populates="hosts")


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    source_type = Column(String(16), nullable=False)  # local | git
    local_path = Column(String(512), nullable=True)
    git_url = Column(String(512), nullable=True)
    git_branch = Column(String(128), default="main")
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String(16), default="never")  # ok | error | never
    sync_message = Column(String(1024), default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(128), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    playbook = Column(String(256), nullable=False)
    inventory_id = Column(Integer, ForeignKey("inventories.id"), nullable=False)
    credential_id = Column(Integer, ForeignKey("credentials.id"), nullable=True)
    extra_vars = Column(Text, default="")
    limit = Column(String(256), default="")
    tags = Column(String(256), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    inventory = relationship("Inventory")
    credential = relationship("Credential")


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)
    status = Column(String(16), default="pending")  # pending|running|success|failed|stopped
    command = Column(Text, default="")
    output = Column(Text, default="")
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    created_by = Column(String(64), default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("Template")


class Setting(Base):
    __tablename__ = "settings"

    key = Column(String(64), primary_key=True)
    value = Column(Text, default="")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=False)
    cron = Column(String(64), nullable=False)
    enabled = Column(Boolean, default=True)
    last_run_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    template = relationship("Template")
