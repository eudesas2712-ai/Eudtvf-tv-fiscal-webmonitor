# Checkpoint — Filtro por Período no Histórico de Relatórios V3

Data: 20260704_235259

## Status

Implementado e validado o filtro por período/data no Histórico de Relatórios V3.

## Backend

Endpoint atualizado:

- GET /reports/history/{project_id}

Novos parâmetros aceitos:

- date_from
- date_to

## Frontend

Página atualizada:

- /reports-history

Campos adicionados:

- Data inicial
- Data final

## Validação

- SEM_DATA_HTTP=200
- COM_DATA_HTTP=200
- SEM_ERRO_API_HISTORY_DATE
- FRONTEND_HISTORY_DATE_OK
- REPORTS_HISTORY_DATE_HTTP=200
