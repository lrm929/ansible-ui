import json
import os
import shutil
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Dict, Optional

from ..config import REPOS_DIR
from ..database import SessionLocal
from ..models import Credential, Host, Project, Task, Template
from .inventory_gen import generate_inventory_file
from .ws_manager import ws_manager

_executor = ThreadPoolExecutor(max_workers=4)

# task_id -> Popen,用于 stop
_processes: Dict[int, subprocess.Popen] = {}
_processes_lock = threading.Lock()

# task_id -> 是否被请求停止
_stop_flags: Dict[int, bool] = {}
_stop_flags_lock = threading.Lock()


def submit_task(task_id: int):
    _executor.submit(run_task, task_id)


def stop_task(task_id: int) -> bool:
    """终止正在运行的任务进程,返回是否找到进程。"""
    with _stop_flags_lock:
        _stop_flags[task_id] = True
    with _processes_lock:
        proc = _processes.get(task_id)
    if proc is None:
        return False
    try:
        proc.terminate()
    except OSError:
        pass
    return True


def _append_output(db, task: Task, line: str):
    task.output = (task.output or "") + line + "\n"
    db.commit()
    ws_manager.broadcast_log(task.id, line)


def run_task(task_id: int):
    db = SessionLocal()
    inv_file = None
    key_file = None
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task is None:
            return
        template = db.query(Template).filter(Template.id == task.template_id).first()
        if template is None:
            task.status = "failed"
            task.finished_at = datetime.utcnow()
            _append_output(db, task, "任务模板不存在,无法执行")
            db.commit()
            ws_manager.broadcast_end(task_id, "failed")
            return

        project = db.query(Project).filter(Project.id == template.project_id).first()
        hosts = db.query(Host).filter(Host.inventory_id == template.inventory_id).all()
        credential = None
        if template.credential_id:
            credential = (
                db.query(Credential).filter(Credential.id == template.credential_id).first()
            )

        task.status = "running"
        task.started_at = datetime.utcnow()
        db.commit()

        # 校验 playbook 路径
        if project is None:
            raise _TaskError("模板关联的项目不存在")
        base_dir = (
            os.path.join(REPOS_DIR, str(project.id))
            if project.source_type == "git"
            else (project.local_path or "")
        )
        playbook_path = os.path.join(base_dir, template.playbook)
        if not os.path.isfile(playbook_path):
            raise _TaskError("playbook 文件不存在: {}".format(playbook_path))

        inv_file, key_file = generate_inventory_file(
            template.inventory, hosts, credential, task_id
        )

        cmd = ["ansible-playbook", "-i", inv_file, playbook_path]
        if template.limit:
            cmd += ["--limit", template.limit]
        if template.tags:
            cmd += ["--tags", template.tags]
        if template.extra_vars:
            try:
                extra = json.loads(template.extra_vars)
            except json.JSONDecodeError:
                raise _TaskError("extra_vars 不是合法的 JSON: {}".format(template.extra_vars))
            cmd += ["-e", json.dumps(extra, ensure_ascii=False)]

        cmd_str = " ".join(cmd)
        task.command = cmd_str
        db.commit()
        _append_output(db, task, "$ " + cmd_str)

        exe = shutil.which("ansible-playbook")
        if exe is None:
            raise _TaskError("未找到 ansible-playbook 命令,请确认已安装 Ansible")
        cmd[0] = exe  # Windows 下需要带扩展名的完整路径才能 CreateProcess

        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            cwd=base_dir,
        )
        with _processes_lock:
            _processes[task_id] = proc

        assert proc.stdout is not None
        for line in proc.stdout:
            _append_output(db, task, line.rstrip("\r\n"))
        proc.wait()

        with _stop_flags_lock:
            stopped = _stop_flags.get(task_id, False)

        if stopped:
            status = "stopped"
            _append_output(db, task, "任务已被手动终止")
        elif proc.returncode == 0:
            status = "success"
            _append_output(db, task, "任务执行成功 (退出码 0)")
        else:
            status = "failed"
            _append_output(db, task, "任务执行失败 (退出码 {})".format(proc.returncode))

        task.status = status
        task.finished_at = datetime.utcnow()
        db.commit()
        ws_manager.broadcast_end(task_id, status)
    except _TaskError as exc:
        _finish_with_error(db, task_id, str(exc))
    except Exception as exc:  # 兜底,绝不能让线程静默崩溃
        _finish_with_error(db, task_id, "任务执行异常: {}".format(exc))
    finally:
        with _processes_lock:
            _processes.pop(task_id, None)
        with _stop_flags_lock:
            _stop_flags.pop(task_id, None)
        for path in (inv_file, key_file):
            if path:
                try:
                    os.remove(path)
                except OSError:
                    pass
        db.close()


def _finish_with_error(db, task_id: int, message: str):
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task is None:
            return
        task.output = (task.output or "") + message + "\n"
        task.status = "failed"
        if task.started_at is None:
            task.started_at = datetime.utcnow()
        task.finished_at = datetime.utcnow()
        db.commit()
        ws_manager.broadcast_log(task_id, message)
        ws_manager.broadcast_end(task_id, "failed")
    except Exception:
        pass


class _TaskError(Exception):
    pass
