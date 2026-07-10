#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
ADMIN_TOKEN="${ADMIN_TOKEN:-troque-este-token-admin}"
PROJECT_ID="${PROJECT_ID:-9b972aa2-f8a4-483b-a7d1-e979d86482fb}"

echo "== TV Fiscal WebMonitor · Smoke Test Strict Auth =="

echo
echo "1) Healthcheck público"
for i in {1..30}; do
  if curl -fsS "$BASE_URL/health" >/dev/null; then
    echo "OK /health"
    break
  fi

  if [ "$i" = "30" ]; then
    echo "ERRO: /health não respondeu após 30 tentativas."
    curl -i "$BASE_URL/health" || true
    exit 1
  fi

  sleep 2
done

echo
echo "2) Scheduler com X-Admin-Token"
curl -fsS -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/admin/scheduler/status" >/dev/null
echo "OK /admin/scheduler/status com header"

echo
echo "3) Scheduler com admin_token via query deve falhar"
STATUS=$(curl -s -o /tmp/tvfiscal_strict_query_test.json -w "%{http_code}" "$BASE_URL/admin/scheduler/status?admin_token=$ADMIN_TOKEN")
if [ "$STATUS" = "200" ]; then
  echo "ERRO: admin_token via query retornou 200 em modo strict."
  cat /tmp/tvfiscal_strict_query_test.json
  exit 1
fi
echo "OK query admin_token bloqueada com HTTP $STATUS"

echo
echo "4) Registry projects com X-Admin-Token"
curl -fsS -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/registry/projects" >/dev/null
echo "OK /registry/projects"

echo
echo "5) Intel summary com X-Admin-Token"
curl -fsS -H "X-Admin-Token: $ADMIN_TOKEN" "$BASE_URL/intel/summary/$PROJECT_ID" >/dev/null
echo "OK /intel/summary"

echo
echo "Smoke strict auth concluído com sucesso."
