# Relatório Completo por Projeto — TV Fiscal WebMonitor

## Objetivo

Esta entrega integra o botão **Gerar Relatório Completo** ao contexto do projeto ativo, usando a estrutura multi-projeto já validada em `/projects`.

O relatório completo consolida:

- nome do projeto;
- cliente contratante;
- segmento;
- portais vinculados;
- anunciantes vinculados e seus papéis;
- evidências auditáveis para checking;
- inteligência de mercado;
- candidatos ao monitoramento de notícias;
- investimento estimado;
- rankings por anunciante e portal;
- leitura executiva automática.

## Novas rotas backend

```text
GET /reports/project/summary/{project_id}
GET /reports/project/pdf/{project_id}
GET /reports/project/pptx/{project_id}
```

As rotas aceitam filtros opcionais:

```text
?date_from=2026-05-01&date_to=2026-05-28
```

## Arquivos adicionados

```text
backend/app/routers/project_reports.py
backend/app/services/project_report_generator.py
```

## Arquivos alterados

```text
backend/app/main.py
frontend/src/app/projects/page.tsx
frontend/src/app/intel/page.tsx
```

## Onde testar

```text
http://localhost:3000/projects
http://localhost:3000/intel?project_id=<PROJECT_ID>
```

## Botões adicionados

Na tela `/projects`:

- Gerar Relatório Completo PPTX;
- Gerar Relatório Completo PDF.

Na tela `/intel`:

- Gerar Relatório Completo PPTX;
- Gerar Relatório Completo PDF.

## Comando de aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Observação operacional

O relatório completo é diferente do relatório Intel simples. O relatório Intel simples mostra o recorte analítico de mercado. O relatório completo por projeto junta configuração operacional, inteligência, checking, portais, anunciantes e candidatos editoriais.
