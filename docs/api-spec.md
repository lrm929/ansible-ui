# Ansible 中文管理平台 — API 契约

前后端共用的接口约定。所有接口前缀 `/api`，除登录外都需要请求头 `Authorization: Bearer <token>`。
所有响应 JSON。错误统一格式：`{"detail": "错误信息"}`，HTTP 状态码语义化（400/401/403/404/409/500）。

## 认证

### POST /api/auth/login
请求：`{"username": "admin", "password": "xxx"}`
响应：`{"token": "jwt-string", "user": {"id": 1, "username": "admin", "role": "admin"}}`

### GET /api/auth/me
响应：`{"id": 1, "username": "admin", "role": "admin"}`

### POST /api/auth/password  （修改自己的密码）
请求：`{"old_password": "...", "new_password": "..."}`
响应：`{"detail": "密码修改成功"}`

## 仪表盘

### GET /api/dashboard
响应：
```json
{
  "hosts": 12,
  "inventories": 3,
  "projects": 2,
  "templates": 5,
  "tasks_total": 40,
  "tasks_today": 3,
  "recent_tasks": [ /* 最近 10 条 Task 对象 */ ],
  "status_stats": {"success": 30, "failed": 8, "running": 2}
}
```

## 凭据 Credentials

### GET /api/credentials → Credential[]
### POST /api/credentials → Credential
### PUT /api/credentials/{id} → Credential
### DELETE /api/credentials/{id} → `{"detail": "已删除"}`

Credential：
```json
{
  "id": 1,
  "name": "生产服务器root",
  "type": "password",          // password | key
  "username": "root",
  "has_secret": true,           // 永不回传密码/私钥明文
  "created_at": "2026-07-29T10:00:00"
}
```
创建/更新请求额外带 `password` 或 `ssh_key` 字段（明文提交，服务端加密存储；更新时不传表示不修改）。

## 主机清单 Inventories

### GET /api/inventories → Inventory[]
### POST /api/inventories → Inventory      `{"name": "...", "description": "..."}`
### PUT /api/inventories/{id} → Inventory
### DELETE /api/inventories/{id}
### GET /api/inventories/{id}/hosts → Host[]
### POST /api/inventories/{id}/hosts → Host
### PUT /api/hosts/{id} → Host
### DELETE /api/hosts/{id}

Inventory：`{"id": 1, "name": "生产环境", "description": "...", "host_count": 5, "created_at": "..."}`

Host：
```json
{
  "id": 1, "inventory_id": 1,
  "hostname": "192.168.1.10",
  "port": 22,
  "group_name": "web",        // 主机所属分组,可空
  "vars": "",                  // 额外 ansible 变量文本,如 "ansible_user=root",可空
  "comment": "web服务器1"
}
```

## 项目 Projects（playbook 来源）

### GET /api/projects → Project[]
### POST /api/projects → Project
```json
{"name": "运维playbook库", "source_type": "local", "local_path": "/opt/playbooks"}
// 或 {"name": "...", "source_type": "git", "git_url": "https://...", "git_branch": "main"}
```
### PUT /api/projects/{id} → Project
### DELETE /api/projects/{id}
### POST /api/projects/{id}/sync → Project   （git 项目: pull/clone；local 项目: 重新扫描）
### GET /api/projects/{id}/playbooks → `{"playbooks": ["site.yml", "roles/deploy/main.yml", ...]}`  （扫描项目目录下所有 .yml/.yaml，相对路径）

Project：`{"id": 1, "name": "...", "source_type": "local|git", "local_path": "...", "git_url": "...", "git_branch": "main", "last_sync_at": "...", "sync_status": "ok|error|never", "sync_message": "..."}`

## 任务模板 Templates

### GET /api/templates → Template[]
### POST /api/templates → Template
### PUT /api/templates/{id} → Template
### DELETE /api/templates/{id}

Template：
```json
{
  "id": 1,
  "name": "部署web服务",
  "project_id": 1,
  "playbook": "site.yml",
  "inventory_id": 1,
  "credential_id": 1,
  "extra_vars": "{\"env\": \"prod\"}",   // JSON 字符串,可空
  "limit": "",                            // ansible --limit,可空
  "tags": "",                             // ansible --tags,可空
  "created_at": "..."
}
```
列表响应中每个 Template 附带 `project_name`、`inventory_name`、`credential_name` 便于展示。

## 任务 Tasks

### POST /api/tasks  请求：`{"template_id": 1}` → Task（异步开始执行）
### GET /api/tasks?limit=50&offset=0 → Task[]
### GET /api/tasks/{id} → Task
### POST /api/tasks/{id}/stop → Task  （终止正在运行的任务）
### GET /api/tasks/{id}/output → `{"output": "完整日志文本"}`

Task：
```json
{
  "id": 1,
  "template_id": 1,
  "template_name": "部署web服务",
  "status": "running",        // pending | running | success | failed | stopped
  "command": "ansible-playbook -i ... site.yml",
  "started_at": "...", "finished_at": null,
  "created_by": "admin",
  "created_at": "..."
}
```

### WebSocket /api/ws/tasks/{task_id}
连接后持续推送执行日志。服务端发送文本帧，每条消息为 JSON：
`{"type": "log", "line": "..."}` / `{"type": "status", "status": "success"}` / `{"type": "end"}`（任务结束后服务端关闭连接）。
前端收到 `end` 后关闭。若连上时任务已结束，服务端直接回全量日志一条 + status + end。

## 定时任务 Schedules

### GET /api/schedules → Schedule[]
### POST /api/schedules → Schedule
### PUT /api/schedules/{id} → Schedule
### DELETE /api/schedules/{id}
### POST /api/schedules/{id}/toggle → Schedule  （启用/禁用切换）

Schedule：
```json
{
  "id": 1,
  "template_id": 1,
  "template_name": "部署web服务",
  "cron": "0 3 * * *",         // 5 段标准 cron
  "enabled": true,
  "last_run_at": null,
  "created_at": "..."
}
```

## 约定补充

- 时间格式 ISO 8601 字符串，后端存 UTC，前端本地格式化显示。
- 列表接口不分页（除 tasks），数据量小直接全量返回数组。
- 后端静态托管前端构建产物：非 `/api`、`/api/ws` 路径全部返回 `frontend/dist/index.html`（SPA fallback）。
- 开发模式前端 vite dev server 端口 5173，proxy `/api` 到 `http://127.0.0.1:8000`。
