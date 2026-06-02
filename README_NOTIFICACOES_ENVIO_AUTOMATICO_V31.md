# TV Fiscal WebMonitor — V31
## Envio real automático por regras

Esta versão fecha a passagem do teste real avulso de SMTP para o fluxo operacional automático do Motor de Notificações.

## Novidades

1. Perfil SMTP por projeto
   - A tela `/admin/notifications` ganhou o bloco **E-mail real automático por regras**.
   - O SMTP validado no teste real pode ser salvo para o projeto.
   - A senha é usada pelo backend para envio automático das regras daquele projeto.

2. Envio real por regras
   - Regras com canal `email` passam a usar o SMTP salvo do projeto.
   - O envio real por e-mail pode funcionar mesmo com `NOTIFICATION_DRY_RUN=true`, mantendo SMS/WhatsApp em simulação.
   - O caminho automático é usado por:
     - botão **Avaliar agora**;
     - avaliação após coleta editorial;
     - avaliação após scheduler.

3. Teste automático
   - Novo botão **Testar e-mail automático**.
   - Diferente do teste real avulso, ele usa o mesmo perfil salvo que será usado pelas regras automáticas.

4. Controle operacional
   - Botão **Salvar SMTP para alertas automáticos**.
   - Botão **Desativar SMTP automático**.
   - Status visível na tela: ativo/pendente, host e remetente.

## Novas rotas

```txt
GET    /notifications/provider-settings/{project_id}
POST   /notifications/provider-settings/{project_id}/email-smtp
DELETE /notifications/provider-settings/{project_id}/email-smtp
POST   /notifications/test-automatic-email/{project_id}
```

## Nova tabela

```txt
notification_provider_settings
```

Campos principais:

```txt
project_id
provider_type
provider_name
active
config
created_at
updated_at
```

## Fluxo recomendado

1. Acesse `/admin/notifications`.
2. Preencha o bloco **Teste real imediato por e-mail SMTP** com os dados validados.
3. Clique em **Salvar SMTP para alertas automáticos**.
4. Clique em **Testar e-mail automático**.
5. Clique em **Avaliar regras e enviar agora**.
6. Confira os logs como `Enviado` e provider `smtp_projeto`.

## Observação de segurança

Para homologação local, a configuração SMTP pode ser salva no banco do projeto. Em produção pública, a recomendação continua sendo usar `.env`, Docker secrets ou secret manager.
