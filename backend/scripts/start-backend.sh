#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

sudo service mariadb start >/dev/null 2>&1 || true

if [ -f .env.local ]; then
  set -a
  # shellcheck disable=SC1091
  source .env.local
  set +a
fi

if [ -z "${DB_PASSWORD:-}" ]; then
  echo "DB_PASSWORD is not set. Copy .env.example to .env.local and fill it in."
  exit 1
fi

if [ -f run/backend.pid ] && kill -0 "$(cat run/backend.pid)" 2>/dev/null; then
  echo "backend already running (pid $(cat run/backend.pid))"
  exit 0
fi

mkdir -p logs run

JAR="$(find target -maxdepth 1 -name 'competition-backend-*.jar' ! -name '*.original' | head -1)"
if [ -z "$JAR" ]; then
  ./mvnw -q -DskipTests package
  JAR="$(find target -maxdepth 1 -name 'competition-backend-*.jar' ! -name '*.original' | head -1)"
fi

nohup java -jar "$JAR" > logs/backend.log 2>&1 &
echo $! > run/backend.pid
echo "backend started (pid $(cat run/backend.pid))"
