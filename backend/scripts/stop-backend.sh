#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f run/backend.pid ] && kill -0 "$(cat run/backend.pid)" 2>/dev/null; then
  kill "$(cat run/backend.pid)"
  rm -f run/backend.pid
  echo "backend stopped"
else
  rm -f run/backend.pid
  echo "backend not running"
fi
