# TV Fiscal WebMonitor — V33
## Caixa de Alertas Operacional

Esta versão adiciona uma camada operacional depois dos disparos automáticos do Motor de Notificações.

## Objetivo

Transformar notificações e alertas enviados em uma fila tratável, com status, responsável e histórico.

## Nova tela

```text
/alerts/inbox
```

## Funcionalidades

- Visualizar alertas por projeto.
- Filtrar por status operacional:
  - Aberto
  - Ciente
  - Adiado
  - Resolvido
  - Todos
- Filtrar por severidade.
- Filtrar por canal.
- Marcar alerta como ciente.
- Adiar alerta por 2 horas.
- Resolver alerta com nota.
- Reabrir alerta.
- Tratar alertas em lote.
- Preservar trilha de atendimento.

## Novas rotas backend

```text
GET  /notifications/inbox/{project_id}
POST /notifications/logs/{log_id}/ack
POST /notifications/logs/{log_id}/resolve
POST /notifications/logs/{log_id}/snooze
POST /notifications/logs/{log_id}/reopen
POST /notifications/logs/{project_id}/bulk-status
```

## Campos adicionados em notification_logs

```text
alert_status
acknowledged_at
acknowledged_by
resolved_at
resolved_by
resolution_note
snoozed_until
```

## Status operacional

```text
aberto    → alerta aguardando tratamento
ciente    → alguém assumiu ciência do alerta
adiado    → alerta pausado temporariamente
resolvido → alerta tratado/encerrado
```

## Uso recomendado

1. O scheduler/coleta editorial gera alertas.
2. O motor envia e-mail real quando regra ativa for acionada.
3. O operador abre `/alerts/inbox`.
4. Marca alertas críticos como ciente.
5. Resolve ou adia conforme necessidade.
6. Mantém histórico para auditoria operacional.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

