#!/usr/bin/env bash
# 阿里云 ECS 每周自动同步流水线：
# 1. 拉取远端最新代码/数据
# 2. 执行采集（含南邮校内通知 + 天池 Playwright + 国际源）→ DeepSeek 审核 → 预计推算 → 预算与数据闸门
# 3. 闸门通过后发布到本机 Nginx 静态目录并推送回 GitHub 备份
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/competition-search}"
ENV_FILE="${ENV_FILE:-/etc/competition-search.env}"

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

cd "${REPO_DIR}"

PYTHON_BIN="${REPO_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" scripts/run_local_sync.py "$@"
bash "${REPO_DIR}/deploy/ecs/deploy_static.sh"
