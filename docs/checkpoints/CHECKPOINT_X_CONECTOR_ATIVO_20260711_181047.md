# Checkpoint — Conector X / Twitter Ativo

## Status

O conector X / Twitter foi ativado com sucesso no Social Monitor.

## Validações realizadas

- Token carregado no backend.
- API do X respondeu com dados reais.
- Coleta manual por query validada.
- Coleta por fonte ativa validada.
- Filtro `platform=x` corrigido e validado no endpoint `/social/summary`.
- Índice único completo criado para upsert em `social_items`.
- Migration idempotente adicionada ao bootstrap.
- Cron ativado de hora em hora.

## Fontes X ativas

- João Pessoa
- Cícero Lucena
- João Azevedo
- Efraim Filho
- Nabor Wanderley
- Lucas Ribeiro
- Veneziano Vital

## Cron

Arquivo: `/etc/cron.d/tvfiscal_social_x`

Frequência: uma vez por hora.

## Observação operacional

A frequência inicial foi definida em 1 hora para preservar créditos da API do X.
