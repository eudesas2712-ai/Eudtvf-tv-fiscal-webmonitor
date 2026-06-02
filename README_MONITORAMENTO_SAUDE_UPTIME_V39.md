# TV Fiscal WebMonitor — V39 Monitoramento de Saúde, Uptime e Auditoria Operacional

## Objetivo

Esta versão adiciona uma camada de confiabilidade operacional para produção, com healthcheck avançado, histórico de disponibilidade, endpoints para monitoramento externo e relatório técnico de saúde da plataforma.

## Novidades

### Nova tela

```text
/admin/system-health
```

### Novas rotas backend

```text
GET  /system/health/advanced
POST /system/health/check
GET  /system/health/history
GET  /system/health/history/export.csv
GET  /system/health/report.pdf
GET  /system/health/uptime
GET  /health/live
GET  /health/ready
```

### Serviços monitorados

```text
PostgreSQL
Redis
MinIO / evidências
Scheduler
Disco
Backup
Motor de notificações
```

### Recursos da tela

```text
Status geral do ambiente
KPIs de serviços OK, atenção e erro
Atividade das últimas 24h
Recomendações operacionais automáticas
Cards por serviço com latência e mensagem técnica
Histórico de healthchecks
Filtros por serviço/status
Exportação CSV
Relatório técnico PDF
Endpoints para UptimeRobot
```

## Banco de dados

Nova tabela:

```text
system_health_checks
```

Ela armazena cada verificação executada, com serviço, status, latência, mensagem, detalhes JSON e origem do disparo.

## Aplicação

Execute:

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/admin/system-health
```

## Testes recomendados

1. Abrir `/admin/system-health`.
2. Confirmar status dos serviços.
3. Clicar em **Executar healthcheck e gravar histórico**.
4. Conferir se o histórico foi populado.
5. Exportar CSV.
6. Gerar PDF técnico.
7. Testar endpoints:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl "http://localhost:8000/system/health/uptime"
```

## UptimeRobot

Recomendação de monitores externos:

```text
/health/live    -> verifica se backend responde
/health/ready   -> verifica backend + PostgreSQL
/system/health/uptime -> verifica saúde ampla e retorna 503 em erro crítico
```

Para produção, configure o UptimeRobot apontando para a URL pública do servidor.

## Observações

- O endpoint `/system/health/advanced` é administrativo e exige token.
- O endpoint `/health/ready` é público e adequado para monitoramento externo.
- O histórico só cresce quando uma verificação é executada e persistida.
- A tabela pode ser limpa futuramente pela rotina de manutenção.
