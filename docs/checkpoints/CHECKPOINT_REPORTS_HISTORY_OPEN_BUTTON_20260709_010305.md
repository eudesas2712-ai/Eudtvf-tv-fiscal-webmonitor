# Checkpoint — Histórico com Botões Baixar e Abrir

Data: 20260709_010305

## Status

Tela de Histórico de Relatórios V3 aprimorada com botão de abertura direta do relatório em nova aba.

## Frontend

Arquivo atualizado:

- frontend/src/app/reports-history/page.tsx

## Implementado

- Campo public_url no tipo ReportItem
- Função openReport
- Botão Baixar PDF com estilo dedicado
- Botão Abrir para visualização em nova aba
- Estilos downloadButtonStyle e openButtonStyle

## Validações

- BUILD_FRONTEND_HISTORICO_BOTOES_ABRIR_FINALIZADO
- FRONTEND_HISTORICO_BOTOES_ABRIR_OK
- REPORTS_HISTORY_OPEN_BUTTON_HTTP=200

## Backup

- data/backups/pos_reports_history_open_button_ok_20260709_005659.tar.gz

## Próxima etapa recomendada

Criar uma área de “Último relatório gerado” no topo do histórico, com botão direto para abrir ou baixar.
