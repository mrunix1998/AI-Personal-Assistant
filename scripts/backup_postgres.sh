#!/usr/bin/env bash
set -euo pipefail
mkdir -p backups
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="backups/assistant_db_${STAMP}.sql"
docker compose exec -T db pg_dump -U postgres -d assistant_db > "$OUT"
echo "Backup written to $OUT"
