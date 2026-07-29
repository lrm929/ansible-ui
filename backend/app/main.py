import asyncio
import json
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .config import FRONTEND_DIST
from .database import Base, SessionLocal, engine
from .models import User
from .routers import (
    auth,
    credentials,
    dashboard,
    inventories,
    projects,
    schedules,
    settings,
    system,
    tasks,
    templates,
    users,
)
from .security import decode_token, hash_password
from .services import scheduler as scheduler_service
from .services.ws_manager import ws_manager

app = FastAPI(title="中文 Ansible 管理平台")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class PermissionMiddleware:
    """全局权限:非 GET 的 /api/* 请求,viewer 一律 403;/api/users* 仅 admin。

    无效/缺失 token 不在此拦截(交给各路由的 get_current_user 返回 401);
    /api/auth/login、/api/auth/password(任何人可改自己的密码)与 WebSocket /api/ws 不受影响。
    """

    EXEMPT_PATHS = ("/api/auth/login", "/api/auth/password")

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        path = scope.get("path", "")
        method = scope.get("method", "GET")
        if (
            path.startswith("/api/")
            and not path.startswith("/api/ws")
            and method != "GET"
            and path not in self.EXEMPT_PATHS
        ):
            role = _role_from_scope(scope)
            if role == "viewer":
                await _reject(send, 403, "只读用户无操作权限")
                return
            if path.startswith("/api/users") and role is not None and role != "admin":
                await _reject(send, 403, "仅管理员可管理用户")
                return
        await self.app(scope, receive, send)


def _role_from_scope(scope):
    for key, value in scope.get("headers", []):
        if key.lower() == b"authorization":
            auth = value.decode("latin-1")
            if auth.lower().startswith("bearer "):
                payload = decode_token(auth[7:].strip())
                if payload:
                    return payload.get("role")
    return None


async def _reject(send, status: int, detail: str):
    body = json.dumps({"detail": detail}, ensure_ascii=False).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


app.add_middleware(PermissionMiddleware)

for module in (auth, dashboard, credentials, inventories, projects, templates, tasks, schedules, settings, users, system):
    app.include_router(module.router)


def _seed_admin():
    db = SessionLocal()
    try:
        if db.query(User).filter(User.username == "admin").first() is None:
            db.add(User(username="admin", password_hash=hash_password("admin123"), role="admin"))
            db.commit()
    finally:
        db.close()


def _migrate():
    """轻量迁移:为已存在的 SQLite 表补充新增列(create_all 不会改已有表)。"""
    new_columns = {
        "inventories": {
            "source_url": "VARCHAR(512)",
            "last_sync_at": "DATETIME",
            "sync_status": "VARCHAR(16) DEFAULT 'never'",
            "sync_message": "TEXT DEFAULT ''",
            "os_type": "VARCHAR(16) DEFAULT 'linux'",
            "exclude_rules": "TEXT DEFAULT ''",
            "credential_id": "INTEGER",
            "default_username": "VARCHAR(128) DEFAULT ''",
            "default_password_encrypted": "TEXT",
            "default_port": "INTEGER",
        },
    }
    with engine.connect() as conn:
        for table, columns in new_columns.items():
            existing = {
                row[1]
                for row in conn.exec_driver_sql(
                    "PRAGMA table_info({})".format(table)
                )
            }
            for column, ddl in columns.items():
                if column not in existing:
                    conn.exec_driver_sql(
                        "ALTER TABLE {} ADD COLUMN {} {}".format(table, column, ddl)
                    )
        conn.commit()


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    _migrate()
    _seed_admin()
    ws_manager.set_loop(asyncio.get_event_loop())
    scheduler_service.start_scheduler()


@app.on_event("shutdown")
def on_shutdown():
    scheduler_service.shutdown_scheduler()


# ---------- 前端静态托管(SPA fallback) ----------
_index_html = os.path.join(FRONTEND_DIST, "index.html")

if os.path.isdir(FRONTEND_DIST):
    assets_dir = os.path.join(FRONTEND_DIST, "assets")
    if os.path.isdir(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa_fallback(full_path: str):
    if os.path.isdir(FRONTEND_DIST):
        # 命中 dist 里的真实文件则直接返回,否则回退 index.html
        candidate = os.path.normpath(os.path.join(FRONTEND_DIST, full_path))
        if (
            full_path
            and candidate.startswith(os.path.normpath(FRONTEND_DIST))
            and os.path.isfile(candidate)
        ):
            return FileResponse(candidate)
        if os.path.isfile(_index_html):
            return FileResponse(_index_html)
    return JSONResponse({"detail": "前端未构建"})
