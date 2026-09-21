#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [ -f run/tunnel.pid ] && kill -0 "$(cat run/tunnel.pid)" 2>/dev/null; then
  echo "tunnel already running (pid $(cat run/tunnel.pid))"
  exit 0
fi

mkdir -p logs run

CLOUDFLARED="${CLOUDFLARED_BIN:-$(command -v cloudflared || true)}"
if [ -z "$CLOUDFLARED" ] && [ -x "/opt/Chat On Steroids/resources/tunnel/cloudflared" ]; then
  CLOUDFLARED="/opt/Chat On Steroids/resources/tunnel/cloudflared"
fi
if [ -z "$CLOUDFLARED" ]; then
  echo "cloudflared not found. Install it or set CLOUDFLARED_BIN."
  exit 1
fi
CONFIG="$HOME/.cloudflared/config.yml"

nohup "$CLOUDFLARED" tunnel --config "$CONFIG" run competition-search-api > logs/tunnel.log 2>&1 &
echo $! > run/tunnel.pid
echo "tunnel started (pid $(cat run/tunnel.pid))"
