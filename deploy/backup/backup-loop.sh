#!/usr/bin/env bash
set -euo pipefail

: "${DB_ROOT_PASSWORD:?DB_ROOT_PASSWORD is required}"

INTERVAL="${BACKUP_INTERVAL_SECONDS:-86400}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
BACKUP_DIR="/backups"

mkdir -p "$BACKUP_DIR"
export MARIADB_PWD="$DB_ROOT_PASSWORD"

while true; do
  timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
  final="$BACKUP_DIR/competition_search-$timestamp.sql.gz"
  temporary="$final.tmp"

  echo "[backup] starting $final"
  if mariadb-dump \
      --host=db \
      --user=root \
      --single-transaction \
      --quick \
      --routines \
      --events \
      competition_search | gzip -9 > "$temporary"; then
    mv "$temporary" "$final"
    echo "[backup] completed $final"
  else
    rm -f "$temporary"
    echo "[backup] failed" >&2
  fi

  find "$BACKUP_DIR" -type f -name "competition_search-*.sql.gz" -mtime "+$RETENTION_DAYS" -delete
  sleep "$INTERVAL"
done
