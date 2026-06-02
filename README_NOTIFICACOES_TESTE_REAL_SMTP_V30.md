# TV Fiscal WebMonitor — V30 — Teste real SMTP imediato

Esta versão adiciona uma área de **teste real por e-mail SMTP** dentro de `/admin/notifications`.

## O que mudou

- Novo endpoint backend:
  - `POST /notifications/test-real-email/{project_id}`
- Nova área na tela:
  - **Teste real imediato por e-mail SMTP**
- Permite enviar um e-mail real mesmo com `NOTIFICATION_DRY_RUN=true`.
- A senha SMTP informada no formulário **não é persistida** no banco.
- O resultado é registrado nos logs como:
  - `sent`, se enviado;
  - `error`, se falhar.

## Uso

Acesse:

```txt
http://localhost:3000/admin/notifications
```

Preencha:

- SMTP Host
- Porta
- Usuário SMTP
- Senha SMTP ou senha de app
- Remetente
- Destinatário
- Assunto
- Mensagem

Depois clique em:

```txt
Enviar e-mail real agora
```

## Observação

SMS e WhatsApp continuam dependentes de provedor real, como Twilio, Zenvia, TotalVoice ou Webhook. O teste real imediato foi liberado primeiro para e-mail porque é o caminho mais simples para homologação operacional.
