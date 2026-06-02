# TV Fiscal WebMonitor — V40.1
## Arquivamento de erros de homologação/teste

Esta atualização complementa a V40 com uma rotina específica para limpar a tela de Saúde do Sistema quando os erros ativos das últimas 24h são resultado de homologação, testes SMTP, testes SMS/WhatsApp, timeout ou tentativas com credenciais incompletas.

## O que muda

- Nova rota backend:
  - `POST /maintenance/archive-homologation-errors`
- Novo bloco na tela:
  - `/admin/maintenance` → **Arquivamento de erros de homologação/teste**
- Os registros não são apagados.
- Os erros são marcados com:
  - `archived_at`
  - `archived_by`
  - `archive_reason`
- O healthcheck passa a ignorar esses erros arquivados.

## Critério de arquivamento

A rotina considera somente registros:

- com `status` igual a `error` ou `erro`;
- ainda não arquivados;
- dentro da janela informada, por padrão as últimas 24h;
- com sinais de teste/homologação, como:
  - título/mensagem contendo “teste”;
  - resposta com SMTP;
  - timeout;
  - conexão fechada;
  - campo SMTP obrigatório ausente;
  - token/credencial;
  - dry-run.

## Fluxo recomendado

1. Acesse `/admin/maintenance`.
2. Vá até **Arquivamento de erros de homologação/teste**.
3. Mantenha `Simular antes de arquivar` marcado.
4. Clique em **Simular homologação**.
5. Verifique o campo `matched`.
6. Se o resultado estiver correto, desmarque a simulação.
7. Clique em **Arquivar homologação**.
8. Acesse `/admin/system-health`.
9. Clique em **Executar healthcheck e gravar histórico**.

## Resultado esperado

A Saúde do Sistema deve sair de:

```text
Notificações: warning
Há X erro(s) ativo(s) de notificação nas últimas 24h.
```

Para:

```text
Notificações: ok
Motor de notificações sem erros ativos recentes.
```

Mantendo o histórico auditável preservado no banco.
