#!/usr/bin/env bash
set -e

PROJECT_ID="9b972aa2-f8a4-483b-a7d1-e979d86482fb"
API="http://localhost:8000"
TOKEN=$(grep -E "^ADMIN_TOKEN=" .env.production | cut -d= -f2- | tr -d '"')

echo "== TV Fiscal WebMonitor · Smoke Test Pós-Restore =="

echo ""
echo "1) Healthcheck"
curl -fsS "$API/health" > /dev/null && echo "OK /health"

echo ""
echo "2) Projetos monitorados"
curl -fsS -H "X-Admin-Token: $TOKEN" "$API/registry/projects" > /dev/null && echo "OK /registry/projects"

echo ""
echo "3) Segmentos"
curl -fsS -H "X-Admin-Token: $TOKEN" "$API/registry/segments" > /dev/null && echo "OK /registry/segments"

echo ""
echo "4) Portais"
curl -fsS -H "X-Admin-Token: $TOKEN" "$API/registry/portals" > /dev/null && echo "OK /registry/portals"

echo ""
echo "5) Anunciantes"
curl -fsS -H "X-Admin-Token: $TOKEN" "$API/registry/advertisers" > /dev/null && echo "OK /registry/advertisers"

echo ""
echo "6) Alertas"
curl -fsS -H "X-Admin-Token: $TOKEN" "$API/alerts/summary/$PROJECT_ID" > /dev/null && echo "OK /alerts/summary"

echo ""
echo "7) Inteligência"
curl -fsS -H "X-Admin-Token: $TOKEN" "$API/intel/summary/$PROJECT_ID" > /dev/null && echo "OK /intel/summary"

echo ""
echo "Smoke test concluído com sucesso."
