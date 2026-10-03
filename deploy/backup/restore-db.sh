#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 || "$2" != "--confirm" ]]; then
  echo "Usage: $0 <backup.sql|backup.sql.gz> --confirm" >&2
  echo "This overwrites data in the competition_search database." >&2
  exit 2
fi

BACKUP="$1"
if [[ ! -f "$BACKUP" ]]; then
  echo "Backup not found: $BACKUP" >&2
  exit 1
fi

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

echo "Stopping backend writes and scheduled backups..."
"${COMPOSE[@]}" stop backend db-backup

restart_services() {
  "${COMPOSE[@]}" start backend db-backup >/dev/null 2>&1 || true
}
trap restart_services EXIT

echo "Restoring $BACKUP into competition_search..."
if [[ "$BACKUP" == *.gz ]]; then
  gzip -dc "$BACKUP"
else
  cat "$BACKUP"
fi | "${COMPOSE[@]}" exec -T db sh -lc \
  'export MARIADB_PWD="$MARIADB_ROOT_PASSWORD"; exec mariadb --user=root competition_search'

trap - EXIT
"${COMPOSE[@]}" start backend db-backup
echo "Restore complete."
