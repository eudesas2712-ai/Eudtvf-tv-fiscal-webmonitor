#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Uso: bash scripts/restore_postgres_prod.sh CAMINHO/postgres_webmonitor.dump"
  exit 1
fi

DUMP_FILE="$1"
cd "$(dirname "$0")/.."
source .env

if [ ! -f "$DUMP_FILE" ]; then
  echo "Dump não encontrado: $DUMP_FILE"
  exit 1
fi

echo "ATENÇÃO: isso irá restaurar o banco ${POSTGRES_DB}."
read -r -p "Digite RESTAURAR para continuar: " CONFIRM
if [ "$CONFIRM" != "RESTAURAR" ]; then
  echo "Operação cancelada."
  exit 1
fi

cat "$DUMP_FILE" | docker compose -f docker-compose.prod.yml exec -T postgres pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists

echo "Restauração concluída."
