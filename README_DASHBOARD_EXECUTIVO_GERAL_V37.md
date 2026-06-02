# TV Fiscal WebMonitor — V37 Dashboard Executivo Geral

## Objetivo

Criar uma visão única de gestão da plataforma, consolidando os módulos de projetos, coletas, publicidade/checking, inteligência de mercado, editorial/notícias, qualificação de marcas, alertas, notificações, SLA e produtividade operacional.

## Nova tela

```text
/
Dashboard Executivo Geral
```

A tela inicial deixa de ser apenas um painel resumido e passa a funcionar como uma central executiva da operação.

## Nova rota backend

```text
GET /executive/dashboard?project_id={opcional}&days=30
```

Quando `project_id` não é informado, a rota consolida todos os projetos disponíveis. Quando informado, filtra os indicadores para o projeto selecionado.

## Arquivos adicionados

```text
backend/app/services/executive_dashboard_service.py
backend/app/routers/executive_dashboard.py
README_DASHBOARD_EXECUTIVO_GERAL_V37.md
```

## Arquivos alterados

```text
backend/app/main.py
frontend/src/app/page.tsx
frontend/src/components/AppShell.tsx
```

## Indicadores consolidados

A nova visão executiva inclui:

```text
- projetos cadastrados e ativos;
- fontes e portais vinculados;
- matérias monitoradas;
- itens visuais capturados;
- itens de mercado;
- investimento estimado;
- evidências auditáveis;
- evidências preservadas;
- candidatos editoriais;
- pendentes de identificação;
- taxa de identificação comercial;
- alertas totais, ativos, vencidos e vencendo;
- alertas sem responsável;
- envios reais, simulados e erros de notificação;
- status de provedores por projeto;
- automações recentes pós-coleta.
```

## Rankings e painéis

```text
- Top anunciantes identificados;
- Top portais publicitários;
- Temas editoriais dominantes;
- Fontes editoriais;
- Alertas por severidade;
- Alertas por canal;
- Alertas por responsável;
- Projetos com maior atividade;
- Linha do tempo operacional;
- Últimos alertas críticos;
- Últimas matérias;
- Últimas evidências visuais.
```

## Leitura executiva automática

O painel gera uma leitura textual com recomendações operacionais, destacando:

```text
- necessidade de qualificação de marcas;
- volume de evidências auditáveis;
- saúde dos alertas e SLA;
- erros de provedores;
- volume editorial;
- investimento estimado.
```

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/
```

## Validação recomendada

```text
1. Abrir a tela inicial.
2. Conferir KPIs de projetos, editorial, mercado e alertas.
3. Conferir se pendentes de identificação aparecem como alerta operacional.
4. Conferir SLA vencido e alertas sem responsável.
5. Abrir atalhos para Intel, Editorial, Caixa de Alertas e SLA.
6. Confirmar que a rota /executive/dashboard responde no Swagger.
```

## Próximo passo sugerido

Após validar a V37, o próximo bloco recomendado é a **V38 — Relatórios Comerciais Automáticos por Cliente/Projeto**, com geração programada e envio por e-mail para clientes internos/externos.
