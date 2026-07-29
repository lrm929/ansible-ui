import asyncio
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
    tasks,
    templates,
)
from .security import hash_password
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

for module in (auth, dashboard, credentials, inventories, projects, templates, tasks, schedules, settings):
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
