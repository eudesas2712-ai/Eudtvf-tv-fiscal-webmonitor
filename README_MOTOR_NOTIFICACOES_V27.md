# TV Fiscal WebMonitor — V27 Motor de Notificações

## Objetivo

Implementa a base operacional para alertas por projeto via painel interno, SMS, e-mail, WhatsApp e webhook. O envio real fica desativado por padrão e pode ser habilitado por variáveis de ambiente quando o provedor for definido.

## Nova tela

```text
/admin/notifications
```

A tela permite:

- cadastrar contatos por projeto;
- configurar canais por contato: painel, SMS, e-mail, WhatsApp e webhook;
- cadastrar regras de alerta;
- criar regras padrão;
- executar avaliação manual;
- enviar testes por canal;
- consultar logs de envio;
- exportar logs em CSV.

## Novas rotas

```text
GET  /notifications/config
GET  /notifications/dashboard/{project_id}
GET  /notifications/contacts/{project_id}
POST /notifications/contacts/{project_id}
PUT  /notifications/contacts/{project_id}/{contact_id}
DELETE /notifications/contacts/{contact_id}

GET  /notifications/rules/{project_id}
POST /notifications/rules/{project_id}
PUT  /notifications/rules/{project_id}/{rule_id}
DELETE /notifications/rules/{rule_id}

POST /notifications/bootstrap/{project_id}
POST /notifications/evaluate/{project_id}
POST /notifications/test/{project_id}

GET  /notifications/logs/{project_id}
GET  /notifications/logs/{project_id}/export.csv
```

## Novas tabelas

```text
notification_contacts
notification_rules
notification_logs
```

## Tipos de evento

```text
editorial_mention       menção de termo/marca/personalidade em matéria
editorial_negative      matéria negativa ou de risco reputacional
executive_alert         alerta vindo da Central de Alertas
checking_auditable      publicidade auditável disponível
any                     qualquer tipo de evento
```

## Fluxo operacional

```text
Coleta editorial / Scheduler
→ Classificação editorial e publicitária
→ Central de Alertas
→ Motor de Notificações avalia regras
→ Painel/SMS/E-mail/WhatsApp/Webhook
→ Log de envio
```

## Variáveis de ambiente

Por padrão, os envios reais ficam simulados:

```env
NOTIFICATION_DRY_RUN=true
NOTIFICATIONS_AUTO_EVALUATE_AFTER_EDITORIAL=true
NOTIFICATIONS_AUTO_EVALUATE_AFTER_SCHEDULER=true

SMS_ENABLED=false
SMS_PROVIDER=webhook
SMS_WEBHOOK_URL=

EMAIL_ALERTS_ENABLED=false
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=

WHATSAPP_ALERTS_ENABLED=false
WHATSAPP_WEBHOOK_URL=

NOTIFICATION_WEBHOOK_URL=
```

Para ativar SMS real, defina `NOTIFICATION_DRY_RUN=false`, `SMS_ENABLED=true` e configure `SMS_WEBHOOK_URL` ou o gateway escolhido.

## Teste recomendado

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/admin/notifications
```

Fluxo de homologação:

1. Informar token administrativo.
2. Cadastrar um contato com telefone/e-mail.
3. Clicar em **Criar regras padrão**.
4. Criar uma regra específica para um termo, marca ou personalidade.
5. Rodar **Avaliar agora**.
6. Testar **Painel**, **SMS**, **E-mail** e **WhatsApp**.
7. Conferir a tabela de logs.

## Integrações automáticas

- Após `/editorial/run/{project_id}`, o sistema avalia regras de notificação se `NOTIFICATIONS_AUTO_EVALUATE_AFTER_EDITORIAL=true`.
- Após varredura de portais pelo scheduler, o sistema avalia regras de notificação se `NOTIFICATIONS_AUTO_EVALUATE_AFTER_SCHEDULER=true`.

## Observação importante

A V27 entrega a estrutura pronta e segura. O envio por SMS/e-mail/WhatsApp permanece em dry-run por padrão para evitar disparos indevidos durante homologação.
