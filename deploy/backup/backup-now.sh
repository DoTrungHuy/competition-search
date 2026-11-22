#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-$(cd "$(dirname "$0")/../.." && pwd)}"
cd "$ROOT"

umask 077
mkdir -p backups
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
output="backups/competition_search-$timestamp.sql.gz"

temporary="$(mktemp "$output.XXXXXX")"
trap 'rm -f -- "$temporary"' EXIT

echo "Writing $output"
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec -T db sh -lc \
  'export MYSQL_PWD="$MARIADB_ROOT_PASSWORD"; exec mariadb-dump --user=root --single-transaction --quick --routines --events competition_search' \
  | gzip -9 > "$temporary"

mv -- "$temporary" "$output"
trap - EXIT
echo "Backup complete: $output"
