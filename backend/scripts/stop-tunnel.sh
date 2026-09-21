#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f run/tunnel.pid ] && kill -0 "$(cat run/tunnel.pid)" 2>/dev/null; then
  kill "$(cat run/tunnel.pid)"
  rm -f run/tunnel.pid
  echo "tunnel stopped"
else
  rm -f run/tunnel.pid
  echo "tunnel not running"
fi
