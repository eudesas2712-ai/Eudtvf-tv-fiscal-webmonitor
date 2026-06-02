# TV Fiscal WebMonitor — Gestão de Projetos Monitorados

## Objetivo

Esta versão adiciona a camada operacional multi-projeto do WebMonitor. A plataforma deixa de depender de um `project_id` fixo na operação diária e passa a permitir a criação e gestão de projetos por cliente, segmento, campanha ou análise competitiva.

## Nova tela

```text
/projects
```

A tela permite:

- listar projetos cadastrados;
- criar novo projeto;
- editar nome, cliente, segmento, descrição e status;
- ativar/desativar escopos de monitoramento;
- vincular portais;
- vincular anunciantes como cliente, concorrente ou monitorado;
- criar/vincular portais padrão ao projeto;
- abrir Intel, Evidências e Intel Comparativo já no contexto do projeto selecionado.

## Novos/atualizados campos de projeto

A tabela `projects` passa a aceitar:

```text
client_name
segment_id
active
monitor_publicity
monitor_editorial
monitor_market
monitor_checking
updated_at
```

A migração é idempotente e executada no bootstrap do backend.

## Backend

Rotas ampliadas em:

```text
/registry/projects
/registry/projects/{project_id}
/registry/projects/{project_id}/config
/registry/projects/{project_id}/portals
/registry/projects/{project_id}/advertisers
/registry/projects/{project_id}/bootstrap-portals
```

## Frontend ajustado

As seguintes telas passam a aceitar `project_id` pela URL:

```text
/intel?project_id=...
/evidencias?project_id=...
/intel/comparativo?project_id=...
```

A tela `/projects` gera esses links automaticamente.

## Scheduler

A seleção de projetos cadastrados agora respeita projetos ativos quando `SNAPSHOT_USE_REGISTERED_PROJECTS=true`.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Teste recomendado

1. Acesse `/projects`.
2. Informe o token administrativo.
3. Crie um projeto, por exemplo: `Saúde PB — Unimed x Hapvida`.
4. Selecione segmento `Saúde`.
5. Vincule portais padrão.
6. Vincule Unimed como cliente e Hapvida como concorrente.
7. Abra Intel, Evidências e Intel Comparativo pelos botões do projeto.
8. Execute a varredura em `/admin/scheduler`.

