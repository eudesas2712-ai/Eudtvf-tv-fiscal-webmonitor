# TV Fiscal WebMonitor — V35
## SLA e Escalonamento de Alertas

Esta versão adiciona controle operacional de SLA para a Caixa de Alertas.

## O que foi implementado

- Nova tela: `/alerts/sla`
- Prazos automáticos por severidade:
  - Crítico: 30 minutos
  - Alto: 120 minutos
  - Médio: 480 minutos
  - Informativo: 1440 minutos
- Campos de SLA nos logs:
  - responsável
  - prazo de atendimento
  - vencimento
  - status de SLA
  - nível/contador de escalonamento
  - data do último escalonamento
- Atribuição de responsável por alerta
- Dashboard de SLA:
  - ativos
  - vencidos
  - vence em breve
  - sem responsável
  - escalados
  - resolvidos
- Escalonamento manual de alertas vencidos por e-mail real, quando o SMTP automático do projeto estiver salvo
- Menu lateral atualizado com “SLA e Escalonamento”

## Novas rotas backend

```text
GET  /notifications/sla/{project_id}
POST /notifications/sla/evaluate/{project_id}
POST /notifications/logs/{log_id}/assign
```

## Campos novos em notification_logs

```text
assigned_to
sla_minutes
sla_due_at
escalation_level
escalation_count
escalated_at
last_escalation_note
```

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/alerts/sla
```

## Fluxo recomendado

1. Abrir `/alerts/sla`.
2. Conferir alertas vencidos e sem responsável.
3. Atribuir responsável aos alertas relevantes.
4. Clicar em “Avaliar SLA e escalar vencidos”.
5. Confirmar logs de escalonamento por e-mail.
6. Resolver ou reabrir itens conforme necessário.

## Observação

SMS e WhatsApp seguem preparados, mas os testes reais desses canais foram deixados para uma etapa futura, conforme decisão operacional. O escalonamento desta versão usa o e-mail real já homologado.
