#!/usr/bin/env bash
#
# Ansible 运维管理平台 一键部署脚本
#
# 用法:
#   bash install.sh                # 默认安装到 /opt/ansible-ui,端口 8000
#   PORT=9000 bash install.sh      # 自定义端口
#   INSTALL_DIR=/srv/ansible-ui bash install.sh
#
# 支持: Rocky/CentOS/RHEL/Alma(dnf|yum)、Debian/Ubuntu(apt)
# 功能: 检查并自动安装依赖(python3/venv/git/ansible)→ 部署代码 → 注册 systemd 服务并启动
#
set -e

INSTALL_DIR="${INSTALL_DIR:-/opt/ansible-ui}"
PORT="${PORT:-8000}"
APP_USER="${APP_USER:-root}"

# ---------- 输出辅助 ----------
info()  { echo -e "\033[32m[信息]\033[0m $*"; }
warn()  { echo -e "\033[33m[警告]\033[0m $*"; }
error() { echo -e "\033[31m[错误]\033[0m $*" >&2; exit 1; }

[ "$(id -u)" = "0" ] || error "请使用 root 运行(或 sudo bash install.sh)"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[ -f "$SCRIPT_DIR/backend/requirements.txt" ] || error "未找到 backend/requirements.txt,请在项目根目录运行本脚本"

# ---------- 包管理器 ----------
PKG=""
if command -v dnf >/dev/null 2>&1; then PKG="dnf"
elif command -v yum >/dev/null 2>&1; then PKG="yum"
elif command -v apt-get >/dev/null 2>&1; then PKG="apt"
else error "不支持的系统:未找到 dnf/yum/apt-get"; fi
info "包管理器: $PKG"

pkg_install() {
  info "安装依赖: $*"
  if [ "$PKG" = "apt" ]; then
    apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq "$@"
  else
    $PKG install -y -q "$@"
  fi
}

# ---------- 依赖检查与安装 ----------
# 1. python3 (>= 3.9)
need_py=0
if ! command -v python3 >/dev/null 2>&1; then
  need_py=1
elif ! python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)'; then
  warn "python3 版本低于 3.9: $(python3 --version 2>&1)"
  need_py=1
fi
if [ "$need_py" = "1" ]; then
  if [ "$PKG" = "apt" ]; then pkg_install python3 python3-venv python3-pip
  else pkg_install python3 python3-pip; fi
fi
PY_VER="$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
info "python3 版本: $PY_VER"

# 2. venv 模块(部分发行版需单独包)
if ! python3 -c 'import ensurepip' >/dev/null 2>&1; then
  warn "缺少 venv/ensurepip 支持,尝试安装"
  if [ "$PKG" = "apt" ]; then pkg_install "python${PY_VER}-venv" || pkg_install python3-venv
  else pkg_install "python${PY_VER}-venv" 2>/dev/null || true; fi
fi

# 3. git(项目 git 同步功能需要)
command -v git >/dev/null 2>&1 || pkg_install git
info "git 版本: $(git --version | awk '{print $3}')"

# ---------- 部署代码 ----------
info "部署代码到 $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
tar --exclude='.git' --exclude='data' --exclude='backend/.venv' \
    --exclude='__pycache__' --exclude='node_modules' --exclude='frontend/dist' \
    -C "$SCRIPT_DIR" -cf - . | tar -C "$INSTALL_DIR" -xf -

# 前端产物:本地已有 dist 则一并复制;没有则提示(需在有 Node 的机器上 npm run build 后重新执行)
if [ -d "$SCRIPT_DIR/frontend/dist" ]; then
  rm -rf "$INSTALL_DIR/frontend/dist"
  cp -r "$SCRIPT_DIR/frontend/dist" "$INSTALL_DIR/frontend/dist"
  info "已复制前端构建产物 frontend/dist"
else
  warn "未发现 frontend/dist,前端页面将无法访问。"
  warn "请在有 Node.js 的机器上执行: cd frontend && npm install && npm run build,然后重新运行本脚本。"
fi

# ---------- Python 虚拟环境与依赖 ----------
info "创建虚拟环境并安装依赖(含 ansible-core,可能需要几分钟)"
cd "$INSTALL_DIR/backend"
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt ansible-core
info "ansible 版本: $(.venv/bin/ansible-playbook --version | head -1)"

# ---------- systemd 服务 ----------
info "注册 systemd 服务 ansible-ui(端口 $PORT)"
cat > /etc/systemd/system/ansible-ui.service << EOF
[Unit]
Description=Ansible UI (中文 Ansible 运维管理平台)
After=network.target

[Service]
Type=simple
User=$APP_USER
WorkingDirectory=$INSTALL_DIR/backend
ExecStart=$INSTALL_DIR/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now ansible-ui

# ---------- 防火墙 ----------
if systemctl is-active firewalld >/dev/null 2>&1; then
  firewall-cmd --permanent --add-port="${PORT}/tcp" >/dev/null && firewall-cmd --reload >/dev/null
  info "firewalld 已放通端口 $PORT"
fi

# ---------- 完成 ----------
sleep 2
if systemctl is-active ansible-ui >/dev/null 2>&1; then
  IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  echo
  info "部署完成!访问: http://${IP:-服务器IP}:$PORT"
  info "默认账号: admin / admin123(请登录后立即修改密码)"
  info "常用命令: systemctl status ansible-ui | journalctl -u ansible-ui -f | systemctl restart ansible-ui"
else
  error "服务启动失败,请执行 journalctl -u ansible-ui -n 50 查看日志"
fi
