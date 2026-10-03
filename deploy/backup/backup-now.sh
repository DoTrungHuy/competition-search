#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

mkdir -p backups
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="backups/competition_search-$timestamp.sql.gz"

echo "Writing $output"
docker compose exec -T db sh -lc \
  'export MARIADB_PWD="$MARIADB_ROOT_PASSWORD"; exec mariadb-dump --user=root --single-transaction --quick --routines --events competition_search' \
  | gzip -9 > "$output"

echo "Backup complete: $output"
