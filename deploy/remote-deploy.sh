#!/usr/bin/env bash
set -Eeuo pipefail

if [[ $# -ne 2 ]]; then
  echo "Usage: $0 <git-sha> <app-dir>" >&2
  exit 2
fi

DEPLOY_SHA="$1"
APP_DIR="$2"

command -v git >/dev/null || { echo "git is required" >&2; exit 1; }
command -v docker >/dev/null || { echo "docker is required" >&2; exit 1; }
docker compose version >/dev/null

cd "$APP_DIR"

test -d .git || { echo "$APP_DIR is not a Git repository" >&2; exit 1; }
test -f .env || { echo "$APP_DIR/.env is missing" >&2; exit 1; }
test -s deploy/certs/origin.pem || { echo "deploy/certs/origin.pem is missing" >&2; exit 1; }
test -s deploy/certs/origin.key || { echo "deploy/certs/origin.key is missing" >&2; exit 1; }

if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "Tracked production files have local changes; refusing to deploy." >&2
  exit 1
fi

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)
PREVIOUS_SHA="$(git rev-parse HEAD)"
ROLLED_BACK=0

rollback() {
  exit_code=$?
  if [[ "$exit_code" -eq 0 || "$ROLLED_BACK" -eq 1 ]]; then
    return
  fi

  ROLLED_BACK=1
  echo "[deploy] deployment failed; rolling application code back to $PREVIOUS_SHA" >&2
  git checkout --detach "$PREVIOUS_SHA" || true
  "${COMPOSE[@]}" up -d --build --remove-orphans || true
  echo "[deploy] application rollback attempted; database was not automatically restored" >&2
}
trap rollback EXIT

echo "[deploy] fetching revision $DEPLOY_SHA"
git fetch --prune origin main
git cat-file -e "${DEPLOY_SHA}^{commit}"

if "${COMPOSE[@]}" ps --status running --services 2>/dev/null | grep -qx db; then
  echo "[deploy] taking pre-deploy database backup"
  bash deploy/backup/backup-now.sh
else
  echo "[deploy] database is not running yet; skipping pre-deploy backup"
fi

git checkout --detach "$DEPLOY_SHA"

echo "[deploy] validating production compose"
"${COMPOSE[@]}" config >/dev/null

echo "[deploy] building and starting production stack"
"${COMPOSE[@]}" up -d --build --remove-orphans

echo "[deploy] waiting for backend health"
for attempt in {1..30}; do
  backend_id="$("${COMPOSE[@]}" ps -q backend 2>/dev/null || true)"
  status=""
  if [[ -n "$backend_id" ]]; then
    status="$(docker inspect --format '{{if .State.Health}}{{.State.Health.Status}}{{end}}' "$backend_id" 2>/dev/null || true)"
  fi
  if [[ "$status" == "healthy" ]]; then
    break
  fi
  if [[ "$attempt" -eq 30 ]]; then
    echo "[deploy] backend did not become healthy" >&2
    "${COMPOSE[@]}" ps >&2 || true
    "${COMPOSE[@]}" logs --tail=120 backend >&2 || true
    exit 1
  fi
  sleep 4
done

echo "[deploy] validating nginx configuration"
"${COMPOSE[@]}" exec -T nginx nginx -t

echo "[deploy] checking HTTPS through local nginx"
health="$(curl --insecure --fail --silent --show-error \
  --resolve api.cs-contest.cn:443:127.0.0.1 \
  https://api.cs-contest.cn/actuator/health)"
printf '%s\n' "$health"
printf '%s' "$health" | grep -q '"status":"UP"'

docker image prune -f >/dev/null || true
trap - EXIT
echo "[deploy] deployed $DEPLOY_SHA successfully"
