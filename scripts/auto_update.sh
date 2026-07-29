#!/usr/bin/env bash
#
# 服务器端自动更新脚本(由 cron 定时调用)
#
# 原理: 检测 GitHub 仓库 main 分支是否有新提交,有则拉取并执行 install.sh 完成部署+重启。
# 前端 dist 已纳入 git,服务器无需 Node 即可运行最新代码。
#
# 安装: 见 README「自动更新」一节。
#
set -u

REPO_DIR="${REPO_DIR:-/opt/ansible-ui-repo}"
BRANCH="${BRANCH:-main}"
LOG_FILE="${LOG_FILE:-/var/log/ansible-ui-autoupdate.log}"

exec >>"$LOG_FILE" 2>&1
echo "===== $(date '+%F %T') 检查更新 ====="

cd "$REPO_DIR" || { echo "[错误] 仓库目录不存在: $REPO_DIR"; exit 1; }

# 更新前清理本地可能的脏改动,保证 pull 永远顺利
git fetch -q origin "$BRANCH" || { echo "[错误] git fetch 失败(网络问题?),本次跳过"; exit 1; }

LOCAL="$(git rev-parse HEAD)"
REMOTE="$(git rev-parse "origin/$BRANCH")"

if [ "$LOCAL" = "$REMOTE" ]; then
  echo "[信息] 已是最新 ($LOCAL),无需更新"
  exit 0
fi

echo "[信息] 发现新版本: $LOCAL -> $REMOTE,开始更新"
git reset --hard -q "origin/$BRANCH"

if bash "$REPO_DIR/install.sh"; then
  echo "[信息] 更新完成,当前版本: $(git rev-parse --short HEAD)"
else
  echo "[错误] install.sh 执行失败,请检查服务状态"
  exit 1
fi
