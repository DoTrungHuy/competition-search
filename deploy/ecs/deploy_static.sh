#!/usr/bin/env bash
# 将仓库中的静态前端资源按 .assetsignore 过滤后同步到 Nginx 站点目录
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/competition-search}"
WEB_ROOT="${WEB_ROOT:-/var/www/competition-search}"

if [[ ! -f "${REPO_DIR}/.assetsignore" ]]; then
  echo "找不到 ${REPO_DIR}/.assetsignore，请检查 REPO_DIR" >&2
  exit 1
fi

mkdir -p "${WEB_ROOT}"

rsync -av --delete \
  --exclude-from="${REPO_DIR}/.assetsignore" \
  "${REPO_DIR}/" "${WEB_ROOT}/"

echo "静态资源已发布至 ${WEB_ROOT}"
