# Checkpoint — Histórico com Filtros Social Monitor

Data: 20260707_210130

## Status

A tela de Histórico de Relatórios V3 passou a exibir filtros para relatórios do Social Monitor.

## Frontend

Arquivo atualizado:

- frontend/src/app/reports-history/page.tsx

Novos filtros adicionados:

- Família: Social Monitor
- Tipo: Executivo Consolidado V3

## Backend

Endpoint validado:

- GET /api/reports/history/{project_id}

Filtro validado:

- report_family=social
- report_type=executive_consolidated_v3

## Resultado validado

Relatório localizado no histórico:

- TVFISCAL_SOCIAL_EXECUTIVO_CONSOLIDADO_PREMIUM_V3.pdf

## Validações

- BUILD_FRONTEND_HISTORICO_SOCIAL_FILTROS_FINALIZADO
- FRONTEND_HISTORICO_SOCIAL_FILTROS_OK
- REPORTS_HISTORY_SOCIAL_PAGE_HTTP=200
- API retornou item social executive_consolidated_v3

## Backup

- data/backups/pos_reports_history_social_filters_ok_20260707_205648.tar.gz

## Próxima etapa recomendada

Adicionar atalho direto da tela Social Monitor para o Histórico de Relatórios filtrado por Social Monitor.
