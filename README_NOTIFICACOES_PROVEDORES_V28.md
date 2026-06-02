# TV Fiscal WebMonitor — V28
## Provedores reais de notificação + limpeza operacional

Esta versão evolui o Motor de Notificações da V27 para operação mais próxima de produção.

## Entregas

- Status dos provedores na tela `/admin/notifications`.
- Botão **Limpar duplicidades** para desativar contatos e regras duplicadas sem excluir histórico.
- Envio real por SMTP quando `EMAIL_ALERTS_ENABLED=true` e `NOTIFICATION_DRY_RUN=false`.
- Envio SMS via:
  - Twilio;
  - Zenvia;
  - TotalVoice;
  - webhook genérico.
- Envio WhatsApp via:
  - Zenvia;
  - webhook genérico.
- Mensagens formatadas por canal:
  - SMS compacto;
  - WhatsApp com estrutura em texto;
  - E-mail com texto e HTML simples.
- Nova rota de diagnóstico:
  - `GET /notifications/provider-status`
- Nova rota de saneamento:
  - `POST /notifications/cleanup/{project_id}`

## Variáveis principais

Modo seguro por padrão:

```env
NOTIFICATION_DRY_RUN=true
```

Para envio real:

```env
NOTIFICATION_DRY_RUN=false
```

### E-mail SMTP

```env
EMAIL_ALERTS_ENABLED=true
SMTP_HOST=smtp.seudominio.com.br
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=usuario
SMTP_PASSWORD=senha
SMTP_FROM=alertas@tvfiscal-pb.com.br
```

### SMS Twilio

```env
SMS_ENABLED=true
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=...
TWILIO_AUTH_TOKEN=...
TWILIO_FROM_NUMBER=+15550000000
```

### SMS Zenvia

```env
SMS_ENABLED=true
SMS_PROVIDER=zenvia
ZENVIA_API_TOKEN=...
ZENVIA_FROM=TVFiscal
```

### SMS TotalVoice

```env
SMS_ENABLED=true
SMS_PROVIDER=totalvoice
TOTALVOICE_ACCESS_TOKEN=...
```

### SMS via webhook genérico

```env
SMS_ENABLED=true
SMS_PROVIDER=webhook
SMS_WEBHOOK_URL=https://seu-webhook/sms
```

### WhatsApp

```env
WHATSAPP_ALERTS_ENABLED=true
WHATSAPP_PROVIDER=webhook
WHATSAPP_WEBHOOK_URL=https://seu-webhook/whatsapp
```

Ou Zenvia:

```env
WHATSAPP_ALERTS_ENABLED=true
WHATSAPP_PROVIDER=zenvia
ZENVIA_API_TOKEN=...
ZENVIA_WHATSAPP_FROM=...
```

## Teste recomendado

```bash
docker compose up -d --build --force-recreate backend frontend
```

Acesse:

```text
http://localhost:3000/admin/notifications
```

Depois:

1. Clique em **Limpar duplicidades**.
2. Confira o bloco **Status dos provedores**.
3. Rode testes por canal.
4. Mantenha `NOTIFICATION_DRY_RUN=true` até cadastrar provedores reais.

