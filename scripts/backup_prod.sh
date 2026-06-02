#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

source .env
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT_DIR="./data/backups/manual_$STAMP"
mkdir -p "$OUT_DIR"

echo "Gerando backup PostgreSQL..."
docker compose -f docker-compose.prod.yml exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$OUT_DIR/postgres_webmonitor.dump"

cat > "$OUT_DIR/manifest.json" <<MANIFEST
{
  "created_at": "$(date -Iseconds)",
  "type": "manual_script",
  "database": "${POSTGRES_DB}",
  "file": "postgres_webmonitor.dump"
}
MANIFEST

zip -r "./data/backups/tvfiscal_backup_$STAMP.zip" "$OUT_DIR"

echo "Backup criado: ./data/backups/tvfiscal_backup_$STAMP.zip"
