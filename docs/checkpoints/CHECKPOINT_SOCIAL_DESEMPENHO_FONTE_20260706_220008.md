# Checkpoint — Desempenho Social por Fonte

Data: 20260706_220008

## Status

Visão analítica de desempenho social por plataforma, fonte e período criada e validada.

## Backend

Endpoint criado:

- GET /api/social/performance/{project_id}

## Frontend

Página atualizada:

- /social

Painel criado:

- Desempenho por Fonte

## Indicadores exibidos

- plataforma
- fonte
- status ativa/inativa
- query monitorada
- total de itens
- patrocinados
- média editorial
- média publicitária
- primeiro item coletado
- último item coletado

## Validações

- BACKEND_SOCIAL_PERFORMANCE_OK
- SOCIAL_PERFORMANCE_HTTP=200
- BUILD_FRONTEND_DESEMPENHO_FONTE_FINALIZADO
- FRONTEND_DESEMPENHO_FONTE_OK
- SOCIAL_DESEMPENHO_FONTE_HTTP=200

## Backup

- data/backups/pos_social_desempenho_fonte_ok_20260706_215755.tar.gz

## Próxima etapa

Criar exportação CSV/Excel do desempenho por fonte e plataforma.
