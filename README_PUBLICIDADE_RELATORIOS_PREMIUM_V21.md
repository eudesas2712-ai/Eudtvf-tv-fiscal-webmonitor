# TV Fiscal WebMonitor — Relatórios Publicitários Premium V21

Esta versão aplica o padrão visual premium aprovado nos relatórios editoriais V20 aos relatórios do módulo publicitário/checking e ao Relatório Completo por Projeto.

## Principais ajustes

- Novo tema compartilhado de relatórios em `backend/app/services/visual_report_theme.py`.
- Relatório Completo por Projeto com cabeçalho navy, logo sem caixa branca, KPI cards, painéis executivos e tabelas premium.
- Intel Comparativo com a mesma linguagem visual premium e separação entre mercado referencial e checking auditável.
- PDF de Inteligência de Mercado Publicitário com template HTML redesenhado.
- Mantida a separação metodológica:
  - Mercado amplo = inteligência referencial;
  - Checking auditável = prova documental;
  - Presença unilateral = apenas um anunciante com dados no recorte;
  - Notícia candidata não é tratada como publicidade.

## Arquivos principais alterados

- `backend/app/services/visual_report_theme.py`
- `backend/app/services/project_report_generator.py`
- `backend/app/services/compare_report_generator.py`
- `backend/app/templates/intel_report.html`

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Testes recomendados

1. Abrir `/projects` e gerar:
   - Relatório Completo PDF em Mercado amplo;
   - Relatório Completo PDF em Checking auditável.
2. Abrir `/intel` e gerar PDF executivo de Inteligência de Mercado.
3. Abrir `/intel/comparativo` e gerar PDF nos modos:
   - Mercado amplo;
   - Somente checking auditável.
4. Conferir se todos os PDFs usam o mesmo padrão visual da V20 editorial.

## Observação

O foco desta versão é padronização visual dos PDFs executivos. As rotas, cálculos e regras de classificação já validadas foram preservadas.
