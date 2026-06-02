# TV Fiscal WebMonitor — V29 Notificações: fuso horário e teste real

## Correção aplicada

O Motor de Notificações agora converte os horários dos logs para o fuso configurado da aplicação.

Padrão:

```env
APP_TIMEZONE=America/Sao_Paulo
TZ=America/Sao_Paulo
```

O banco pode continuar gravando UTC internamente; a API passa a devolver `created_at_display` no horário local, evitando diferença de +3 horas no painel.

## Teste real de envio

Enquanto `NOTIFICATION_DRY_RUN=true`, SMS, WhatsApp e e-mail são simulados. Para envio real:

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
SMTP_FROM=alertas@seudominio.com.br
```

### SMS via Twilio

```env
SMS_ENABLED=true
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM_NUMBER=
```

### SMS via webhook

```env
SMS_ENABLED=true
SMS_PROVIDER=webhook
SMS_WEBHOOK_URL=https://seu-gateway/sms
```

### WhatsApp via webhook

```env
WHATSAPP_ALERTS_ENABLED=true
WHATSAPP_PROVIDER=webhook
WHATSAPP_WEBHOOK_URL=https://seu-gateway/whatsapp
```

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/admin/notifications
```

Confira o bloco “Status dos provedores” e valide a hora local exibida.
