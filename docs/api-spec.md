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
### POST /api/inventories/{id}/hosts/import  （multipart 上传文件,字段名 file）
解析文件导入主机,按 (inventory_id, hostname) upsert。响应:`{"added": 3, "updated": 2, "excluded": 1, "errors": ["第5行: 主机名为空"]}`
支持的文件格式(按扩展名/内容自动识别):
- **CSV**:支持带表头(`hostname,port,group_name,vars,comment`,列可缺省、顺序不限)或无表头(每行第一列为主机名,其余忽略)。编码自动识别 utf-8-sig / gbk。
- **资产 TXT(.txt)**:每行 `昵称<分隔>IP<分隔>组名`,分隔符支持 Tab / 逗号 / 连续空白。映射:IP→hostname、组名→group_name、昵称→comment。
### POST /api/inventories/{id}/sync  （从 source_url 拉取主机列表）
要求清单已配置 source_url(未配置返回 400)。GET 该 URL,按内容自动识别格式:
- JSON 数组(`[{"hostname": "...", "port": 22, ...}]`)
- CSV(规则同上传)
- **LoadGameData 资产接口**:无换行的 `|` 分隔字段流,每条记录固定 18 列(末两列为空),取第 3 列为服务器 IP(hostname)、第 6 列为昵称(comment);分组取昵称前缀——去掉昵称尾部数字再去掉末尾的 `_`/`-` 即为前缀,前缀相同的机器归为一组(group_name)。

**同步为全量替换语义**:upsert 后,清单中不在本次拉取结果里的主机一律删除,保证清单与源完全一致。响应:`{"added": 3, "updated": 2, "removed": 5, "excluded": 0, "errors": []}`。若解析结果 0 条且 errors 非空(疑似源数据异常),不执行删除,返回 502 并置 sync_status=error(防止源故障清空清单)。

更新清单 sync_status/sync_message/last_sync_at。

Inventory：`{"id": 1, "name": "生产环境", "description": "...", "host_count": 5, "created_at": "...", "source_url": null, "last_sync_at": null, "sync_status": "never|ok|error", "sync_message": ""}`

创建/更新清单时可选字段:
- `source_url`: HTTP API 地址,返回 JSON 数组或 CSV 主机列表
- `os_type`: `linux`(默认) / `windows`;windows 生成 inventory 时用 winrm 连接,默认端口 5985
- `exclude_rules`: 排除规则文本,每行一条;import/sync 时主机名或分组名包含任一规则(不区分大小写)即跳过
- `credential_id`: 绑定凭据(可空);执行任务时优先级: 模板凭据 > 清单凭据 > 清单默认账号密码
- `default_username` / `default_password` / `default_port`: 未绑定凭据时的兜底连接参数;default_password 加密存储,响应永不回传,以 `has_default_password` 表示;default_port 可空(linux 默认 22,windows 默认 5985)

import / sync 响应增加 `"excluded": 2`(被排除规则跳过的数量)。

Inventory 响应对象增加以上字段(除 default_password)。

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

## 通知设置 Webhook（企业微信）

### GET /api/settings/webhook → WebhookConfig
### PUT /api/settings/webhook → WebhookConfig
### POST /api/settings/webhook/test → `{"detail": "测试消息已发送"}`（发送失败返回 502 + 原因）

WebhookConfig：
```json
{
  "webhook_url": "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx",
  "enabled": true,
  "notify_on_success": true,
  "notify_on_failure": true
}
```

通知触发时机：任务执行结束（success / failed / stopped）后，若 enabled 且对应状态开关打开，向 webhook_url POST 企业微信 markdown 消息。通知发送失败只记录日志，不影响任务状态。

## 系统信息 System（系统名称 / 登录背景）

### GET /api/system/info → `{"site_name": "Ansible 运维管理平台", "has_login_bg": false}`  （**公开**,登录页要用）
### PUT /api/system/info → 同左  `{"site_name": "新名称"}`
### POST /api/system/login-bg  （multipart 上传图片,字段名 file;jpg/png/webp,≤2MB）→ `{"detail": "已更新"}`
### GET /api/system/login-bg  （**公开**,返回图片;未设置 404）
### DELETE /api/system/login-bg → `{"detail": "已删除"}`

登录页标题与主界面菜单标题均显示 site_name;登录页背景在设置了图片时使用图片(全屏覆盖 + 半透明遮罩保证表单可读)。

## 用户与权限

角色:`admin`(全部权限 + 用户管理)/ `operator`(除用户管理外的全部操作)/ `viewer`(只读,仅 GET)。
全局规则(中间件实现):非 GET 的 `/api/*` 请求,viewer 一律 403;`/api/users*` 仅 admin。
种子的 admin 用户角色为 admin。

### GET /api/users → User[]           （仅 admin）
### POST /api/users → User            （仅 admin）`{"username": "...", "password": "...", "role": "operator"}`
### PUT /api/users/{id} → User        （仅 admin）`{"role": "viewer", "password": "..."}` 均可选,改角色/重置密码
### DELETE /api/users/{id}            （仅 admin）不能删除自己,不能删除最后一个 admin

User:`{"id": 2, "username": "ops", "role": "operator", "created_at": "..."}`

## Playbook 文件管理

仅 `source_type=local` 的项目支持写操作(git 项目只读,写接口返回 400)。path 为项目内相对路径,必须以防目录穿越(`..` 拒绝 400)。

### GET /api/projects/{id}/playbooks/{path} → `{"path": "site.yml", "content": "..."}`
### POST /api/projects/{id}/playbooks → 同对象;已存在返回 409;自动创建子目录
### PUT /api/projects/{id}/playbooks/{path} → `{"path": "...", "content": "..."}`
### DELETE /api/projects/{id}/playbooks/{path} → `{"detail": "已删除"}`

## 约定补充

- 时间格式 ISO 8601 字符串，后端存 UTC，前端本地格式化显示。
- 列表接口不分页（除 tasks），数据量小直接全量返回数组。
- 后端静态托管前端构建产物：非 `/api`、`/api/ws` 路径全部返回 `frontend/dist/index.html`（SPA fallback）。
- 开发模式前端 vite dev server 端口 5173，proxy `/api` 到 `http://127.0.0.1:8000`。
