#!/usr/bin/env bash
set -euo pipefail

cd /opt/tvfiscal-webmonitor

LOCK="/tmp/tvfiscal_social_youtube_collect.lock"
exec 9>"$LOCK"
flock -n 9 || exit 0

set -a
source .env.production
set +a

PROJECT_ID="${SOCIAL_AUTOCOLLECT_PROJECT_ID:-9b972aa2-f8a4-483b-a7d1-e979d86482fb}"
MAX_RESULTS="${YOUTUBE_MAX_RESULTS:-15}"
TS="$(date '+%Y-%m-%d %H:%M:%S')"

echo "[$TS] INICIO coleta social/youtube projeto=$PROJECT_ID"

SOURCES=$(docker compose --env-file .env.production -f docker-compose.prod.yml exec -T postgres \
  psql -U webmonitor -d webmonitor -Atc "SELECT id FROM social_sources WHERE project_id='${PROJECT_ID}'::uuid AND platform='youtube' AND active IS TRUE ORDER BY created_at;")

if [ -z "$SOURCES" ]; then
  echo "[$TS] Nenhuma fonte YouTube ativa encontrada."
  exit 0
fi

for SOURCE_ID in $SOURCES; do
  echo "[$TS] Coletando source_id=$SOURCE_ID"
  curl -sS -X POST \
    -H "X-Admin-Token: $ADMIN_TOKEN" \
    "http://127.0.0.1:8000/social/youtube/collect/$PROJECT_ID?source_id=$SOURCE_ID&max_results=$MAX_RESULTS" \
    || true
  echo
done

echo "[$TS] FIM coleta social/youtube"
