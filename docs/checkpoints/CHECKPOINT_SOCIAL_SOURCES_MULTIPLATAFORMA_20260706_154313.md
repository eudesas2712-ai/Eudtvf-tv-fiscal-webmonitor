# Checkpoint — Social Sources Multiplataforma

Data: 20260706_154313

## Status

Social Monitor e Gestão de Fontes Sociais atualizados para base multiplataforma.

## Frontend

Páginas atualizadas:

- /social
- /social-sources

## Plataformas habilitadas

- YouTube
- Instagram
- Facebook
- X / Twitter
- TikTok
- LinkedIn

## Funcionalidades validadas

- /social com filtro por plataforma
- /social com coleta rápida dinâmica
- /social-sources com cadastro por plataforma
- /social-sources com coleta manual dinâmica para YouTube e X / Twitter
- plataformas ainda sem conector retornam aviso controlado
- relatórios Social V3 aceitam platform

## Backend

Arquivos atualizados:

- backend/app/routers/social.py
- backend/app/routers/social_reports.py
- backend/app/services/social_x_collector.py

## Coletor X / Twitter

Rota criada:

- POST /api/social/x/collect/{project_id}

Validação atual:

- Sem token configurado, retorna erro controlado:
  Token do X / Twitter não configurado. Defina X_BEARER_TOKEN no .env.production.

## Validações

- FRONTEND_SOCIAL_MULTIPLATFORM_OK
- SOCIAL_PAGE_HTTP=200
- BACKEND_X_COLLECTOR_OK
- SOCIAL_X_COLLECT_HTTP=200
- SEM_ERRO_ROTA_X_COLLECT
- FRONTEND_COLLECT_SOCIAL_MULTIPLATFORM_OK
- SOCIAL_PAGE_COLLECT_MULTIPLATFORM_HTTP=200
- FRONTEND_SOCIAL_SOURCES_MULTIPLATFORM_OK
- SOCIAL_SOURCES_PAGE_HTTP=200

## Próxima etapa

Criar script operacional para coleta X / Twitter por fontes ativas, deixando preparado para cron após configuração do token X_BEARER_TOKEN.
