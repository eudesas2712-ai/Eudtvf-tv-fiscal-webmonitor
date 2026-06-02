#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "Arquivo .env não encontrado. Copie .env.production.example para .env e configure os segredos."
  exit 1
fi

mkdir -p data/postgres data/redis data/minio data/backups data/exports data/logs

docker compose -f docker-compose.prod.yml up -d --build

echo "Aguardando backend..."
sleep 10
curl -f http://127.0.0.1:8000/health/live
curl -f http://127.0.0.1:8000/health/ready

echo "Deploy concluído."
