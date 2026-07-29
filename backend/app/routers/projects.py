import os
import subprocess
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config import REPOS_DIR
from ..database import get_db
from ..deps import get_current_user
from ..models import Project, User
from ..schemas import PlaybooksResponse, ProjectCreate, ProjectOut, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["项目"])


def _get_project(db: Session, project_id: int) -> Project:
    project = db.query(Project).filter(Project.id == project_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return project


def _project_dir(project: Project) -> str:
    if project.source_type == "git":
        return os.path.join(REPOS_DIR, str(project.id))
    return project.local_path or ""


def _validate_payload(source_type: str, local_path, git_url):
    if source_type not in ("local", "git"):
        raise HTTPException(status_code=400, detail="source_type 必须是 local 或 git")
    if source_type == "local":
        if not local_path:
            raise HTTPException(status_code=400, detail="local 项目必须提供 local_path")
        if not os.path.isdir(local_path):
            raise HTTPException(status_code=400, detail="本地路径不存在: {}".format(local_path))
    else:
        if not git_url:
            raise HTTPException(status_code=400, detail="git 项目必须提供 git_url")


@router.get("", response_model=List[ProjectOut])
def list_projects(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    return db.query(Project).order_by(Project.id).all()


@router.post("", response_model=ProjectOut)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _validate_payload(payload.source_type, payload.local_path, payload.git_url)
    project = Project(
        name=payload.name,
        source_type=payload.source_type,
        local_path=payload.local_path,
        git_url=payload.git_url,
        git_branch=payload.git_branch or "main",
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.put("/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project(db, project_id)
    for field in ("name", "source_type", "local_path", "git_url", "git_branch"):
        value = getattr(payload, field)
        if value is not None:
            setattr(project, field, value)
    _validate_payload(project.source_type, project.local_path, project.git_url)
    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id}")
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project(db, project_id)
    db.delete(project)
    db.commit()
    return {"detail": "已删除"}


@router.post("/{project_id}/sync", response_model=ProjectOut)
def sync_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project(db, project_id)
    if project.source_type == "local":
        path = project.local_path or ""
        if os.path.isdir(path):
            project.sync_status = "ok"
            project.sync_message = "本地路径校验成功"
        else:
            project.sync_status = "error"
            project.sync_message = "本地路径不存在: {}".format(path)
    else:
        repo_dir = os.path.join(REPOS_DIR, str(project.id))
        try:
            if os.path.isdir(os.path.join(repo_dir, ".git")):
                result = subprocess.run(
                    ["git", "-C", repo_dir, "pull"],
                    capture_output=True, text=True, timeout=300,
                )
            else:
                os.makedirs(REPOS_DIR, exist_ok=True)
                result = subprocess.run(
                    ["git", "clone", "--branch", project.git_branch or "main",
                     project.git_url, repo_dir],
                    capture_output=True, text=True, timeout=600,
                )
            if result.returncode == 0:
                project.sync_status = "ok"
                project.sync_message = "同步成功"
            else:
                project.sync_status = "error"
                project.sync_message = (result.stderr or result.stdout or "git 执行失败").strip()[-500:]
        except FileNotFoundError:
            project.sync_status = "error"
            project.sync_message = "未找到 git 命令,请确认已安装 Git"
        except subprocess.TimeoutExpired:
            project.sync_status = "error"
            project.sync_message = "git 同步超时"
    project.last_sync_at = datetime.utcnow()
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}/playbooks", response_model=PlaybooksResponse)
def list_playbooks(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = _get_project(db, project_id)
    base_dir = _project_dir(project)
    playbooks = []
    if base_dir and os.path.isdir(base_dir):
        for root, dirs, files in os.walk(base_dir):
            dirs[:] = [d for d in dirs if d != ".git"]
            for filename in sorted(files):
                if filename.endswith((".yml", ".yaml")):
                    full = os.path.join(root, filename)
                    rel = os.path.relpath(full, base_dir).replace("\\", "/")
                    playbooks.append(rel)
    playbooks.sort()
    return {"playbooks": playbooks}
