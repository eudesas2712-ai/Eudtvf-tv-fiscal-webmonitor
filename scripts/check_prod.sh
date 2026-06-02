#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

docker compose -f docker-compose.prod.yml ps

echo "\nHealth live:"
curl -s http://127.0.0.1:8000/health/live || true

echo "\nHealth ready:"
curl -s http://127.0.0.1:8000/health/ready || true

echo "\nUptime:"
curl -s http://127.0.0.1:8000/system/health/uptime || true

echo "\nLogs backend recentes:"
docker compose -f docker-compose.prod.yml logs backend --tail=80
