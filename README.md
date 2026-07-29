# Ansible 运维管理平台

参考 [Semaphore UI](https://github.com/semaphoreui/semaphore) 实现的**全中文** Ansible Web 管理工具:在浏览器里管理主机清单、凭据、Playbook 项目,一键执行任务并实时查看日志,支持定时调度。

## 功能

- 📊 仪表盘:主机/任务统计、最近执行记录
- 🖥️ 主机清单:分组管理主机,支持 CSV 上传导入与 HTTP API 自动拉取
- 🔑 凭据管理:SSH 密码 / 私钥,Fernet 加密存储,永不回传明文
- 📦 项目管理:本地目录或 Git 仓库方式接入 Playbook,一键同步
- 📋 任务模板:Playbook + 清单 + 凭据 + extra_vars/limit/tags 组合成可复用模板
- ▶️ 任务执行:WebSocket 实时日志、停止任务、完整历史记录
- ⏰ 定时任务:标准 cron 表达式调度模板执行
- 📢 通知:企业微信 webhook 任务结果通知
- 👤 用户:登录认证、修改密码

## 技术栈

| 端 | 技术 |
|----|------|
| 后端 | FastAPI + SQLite + APScheduler,子进程调用 `ansible-playbook` |
| 前端 | Vue3 + Vite + Element Plus(简体中文) |

## 快速开始

要求:Python ≥ 3.9、Node ≥ 18、Ansible(执行任务的服务器上需安装;Windows 开发建议 WSL)。

```bash
# 1. 后端
cd backend
python -m venv .venv
source .venv/Scripts/activate    # Git Bash;CMD 用 .venv\Scripts\activate.bat
pip install -r requirements.txt
python run.py                    # http://127.0.0.1:8000

# 2. 前端(开发模式,另开终端)
cd frontend
npm install
npm run dev                      # http://127.0.0.1:5173,已配置代理到 8000
```

默认账号:**admin / admin123**,登录后请立即修改密码。

## 生产部署

一键脚本（自动检查并安装 python3/venv/git/ansible 依赖，注册 systemd 服务并启动）:

```bash
git clone https://github.com/lrm929/ansible-ui.git
cd ansible-ui
# 前端需先构建(本机有 Node 时): cd frontend && npm install && npm run build && cd ..
sudo bash install.sh          # 默认 /opt/ansible-ui,端口 8000;PORT=9000 可改
```

或手动部署：

```bash
cd frontend && npm run build     # 产物输出到 frontend/dist
cd ../backend && python run.py   # 后端直接托管 dist,访问 http://服务器IP:8000
```

建议配合 nginx/caddy 反向代理 + systemd/supervisor 守护进程。

## 自动更新(服务器)

在服务器上克隆仓库并配置 cron,即可实现「推送到 GitHub 后自动部署重启」:

```bash
git clone https://github.com/lrm929/ansible-ui.git /opt/ansible-ui-repo
chmod +x /opt/ansible-ui-repo/scripts/auto_update.sh
( crontab -l 2>/dev/null; echo "*/5 * * * * /opt/ansible-ui-repo/scripts/auto_update.sh" ) | crontab -
```

原理:`auto_update.sh` 每 5 分钟检查 `origin/main` 是否有新提交,有则拉取并执行 `install.sh` 完成部署与重启,日志在 `/var/log/ansible-ui-autoupdate.log`。

> 前端 `dist` 已纳入 git,**本地提交前务必先 `cd frontend && npm run build`**,否则服务器拉到的是旧界面。

## 目录结构

```
├── backend/          FastAPI 后端(app/ 下含路由与执行器)
├── frontend/         Vue3 前端(src/views 各页面)
├── docs/api-spec.md  前后端 API 契约
└── data/             运行时数据(SQLite、密钥、git 克隆),不入库
```

## 路线图

- [ ] 多用户与角色权限(管理员/操作员/只读)
- [ ] Ansible Galaxy role 安装支持
- [ ] 任务执行前的 dry-run(--check)模式
- [ ] Docker 一键部署

## 开源协议

MIT
