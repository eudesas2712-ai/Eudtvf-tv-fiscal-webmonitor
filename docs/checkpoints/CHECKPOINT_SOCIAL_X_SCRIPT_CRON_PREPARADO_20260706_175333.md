# Checkpoint — Coletor X / Twitter Preparado

Data: 20260706_175333

## Status

Coletor operacional X / Twitter preparado no TV Fiscal WebMonitor.

## Arquivos criados/atualizados

- backend/app/services/social_x_collector.py
- backend/app/routers/social.py
- scripts/collect_social_x_active.sh
- /etc/cron.d/tvfiscal_social_x

## Rota backend criada

- POST /api/social/x/collect/{project_id}

## Script operacional

- scripts/collect_social_x_active.sh

Recursos:

- lock próprio para evitar execução duplicada
- leitura segura do .env.production
- consulta somente fontes platform='x' ativas
- encerramento seguro quando não há fontes X ativas
- encerramento seguro quando X_BEARER_TOKEN não está configurado
- chamada interna para 127.0.0.1:8000/social/x/collect/{project_id}

## Cron

Arquivo criado:

- /etc/cron.d/tvfiscal_social_x

Status:

- preparado
- desativado
- linha de execução comentada até configuração de X_BEARER_TOKEN

## Validações

- SCRIPT_X_COLLECT_SYNTAX_OK
- SCRIPT_X_MANUAL_OK
- Sem fontes X: Nenhuma fonte X / Twitter ativa encontrada
- Com fonte X temporária e sem token: X_BEARER_TOKEN não configurado
- Fonte temporária removida com sucesso
- CRON_X_PREPARADO_DESATIVADO_OK

## Próxima etapa

Configurar X_BEARER_TOKEN no .env.production, cadastrar fontes X reais e ativar o cron X / Twitter.
