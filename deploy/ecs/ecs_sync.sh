#!/usr/bin/env bash
# 阿里云 ECS 每周自动同步流水线：
# 1. 拉取远端最新代码/数据
# 2. 执行采集（含南邮校内通知 + 国际源）→ AI 审核 → 自动发布 AI 通过项 → 预计报名推算 → 预算与数据闸门
# 3. 闸门通过后同步至本机 MariaDB 后端，并推送回 GitHub
set -euo pipefail

REPO_DIR="${REPO_DIR:-/opt/competition-search}"
ENV_FILE="${ENV_FILE:-${REPO_DIR}/.env}"

if [[ -f "${ENV_FILE}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
  set +a
fi

cd "${REPO_DIR}"

# 始终对齐远端 main，避免本机 --no-push 残留提交与 GitHub Actions 产生 rebase 冲突
git fetch origin main
git reset --hard origin/main

PYTHON_BIN="${REPO_DIR}/.venv/bin/python"
if [[ ! -x "${PYTHON_BIN}" ]]; then
  PYTHON_BIN="python3"
fi

"${PYTHON_BIN}" scripts/run_local_sync.py --skip kaggle --no-pull --no-push "$@"

API_BASE="http://127.0.0.1:${API_PORT:-8088}"
if [[ -n "${SYNC_TOKEN:-}" ]]; then
  curl --fail-with-body --silent --show-error --retry 3 --connect-timeout 15 \
    -H "Content-Type: application/json" \
    -H "X-Sync-Token: ${SYNC_TOKEN}" \
    --data-binary @data/competitions.json \
    "${API_BASE}/api/internal/sync"
  echo
  curl --fail-with-body --silent --show-error --retry 3 --connect-timeout 15 \
    -H "Content-Type: application/json" \
    -H "X-Sync-Token: ${SYNC_TOKEN}" \
    --data-binary @data/review_queue.json \
    "${API_BASE}/api/internal/review-candidates/sync"
  echo
fi
