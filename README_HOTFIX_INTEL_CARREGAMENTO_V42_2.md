# TV Fiscal WebMonitor — Hotfix Intel Carregamento V42.2

## Objetivo
Corrigir travamento do painel `/intel` em "Carregando..." após a ativação das permissões finas da V42.

## Causa provável
A página `/intel` carregava o resumo, histórico, evidências, segmentos e anunciantes em sequência. Caso uma chamada complementar demorasse, falhasse por permissão, timeout ou volume alto, o painel podia permanecer em estado de carregamento, mesmo para usuário Administrador.

## Correções
- O resumo `/intel/summary/{project_id}` agora é carregado primeiro e libera o painel principal.
- Histórico, evidências, segmentos e anunciantes passaram a carregar como dados complementares.
- Dados complementares usam `Promise.allSettled`, sem travar o painel.
- Chamadas complementares têm timeout.
- Evidências no Intel foram reduzidas para `limit=250` para evitar lentidão inicial.
- Se algum complemento falhar, o painel continua carregado e mostra aviso operacional.

## Arquivo alterado
- `frontend/src/app/intel/page.tsx`

## Aplicação
```bash
docker compose -f docker-compose.yml -f docker-compose.backup-volume.override.yml up -d --build --force-recreate backend frontend
```

## Testes
1. Entrar como Administrador.
2. Abrir `/intel`.
3. Confirmar que os KPIs carregam.
4. Conferir aviso se algum dado complementar falhar.
5. Testar PDF/PPTX.
6. Testar usuário sem módulo Intel para confirmar bloqueio.
