# TV Fiscal WebMonitor — V34 — SMS e WhatsApp Real

Esta versão libera a homologação e o envio automático por regras usando SMS e WhatsApp, no mesmo padrão já aprovado para e-mail real.

## Novos recursos

- Teste real imediato por SMS em `/admin/notifications`.
- Teste real imediato por WhatsApp em `/admin/notifications`.
- Cadastro de provedor SMS por projeto.
- Cadastro de provedor WhatsApp por projeto.
- Envio automático por regra usando SMS real, mesmo com `NOTIFICATION_DRY_RUN=true`, quando houver provedor salvo no projeto.
- Envio automático por regra usando WhatsApp real, mesmo com `NOTIFICATION_DRY_RUN=true`, quando houver provedor salvo no projeto.
- Logs separados por canal, provedor e resposta.
- Preservação do fluxo já homologado de e-mail SMTP.

## Provedores SMS suportados

- Webhook genérico
- Twilio
- Zenvia
- TotalVoice

## Provedores WhatsApp suportados

- Webhook genérico
- Zenvia
- Meta WhatsApp Cloud API

## Novas rotas backend

```text
POST   /notifications/provider-settings/{project_id}/sms
DELETE /notifications/provider-settings/{project_id}/sms
POST   /notifications/provider-settings/{project_id}/whatsapp
DELETE /notifications/provider-settings/{project_id}/whatsapp

POST   /notifications/test-real-sms/{project_id}
POST   /notifications/test-real-whatsapp/{project_id}
POST   /notifications/test-automatic-sms/{project_id}
POST   /notifications/test-automatic-whatsapp/{project_id}
```

## Fluxo recomendado

1. Abrir `/admin/notifications`.
2. Conferir contato ativo com telefone SMS e/ou WhatsApp.
3. Em regra ativa, incluir os canais `sms` e/ou `whatsapp`.
4. Configurar o provedor SMS ou WhatsApp no bloco novo.
5. Testar envio real imediato.
6. Salvar provedor para alertas automáticos.
7. Testar envio automático.
8. Executar `Avaliar regras e enviar agora` ou aguardar a coleta/scheduler.

## Webhook genérico

O webhook recebe um POST JSON semelhante a:

```json
{
  "to": "83999999999",
  "message": "TV Fiscal Alerta...",
  "title": "Título do alerta",
  "channel": "sms",
  "event": {
    "event_type": "editorial_mention",
    "severity": "alto",
    "category": "editorial"
  }
}
```

Para WhatsApp, o campo `channel` vai como `whatsapp`.

## Observação operacional

Para WhatsApp, recomenda-se API oficial, Zenvia, Meta Cloud API, Take Blip, 360dialog ou webhook próprio. Evite automação com número pessoal comum, pois há risco de bloqueio.
