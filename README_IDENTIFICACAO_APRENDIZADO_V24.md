# TV Fiscal WebMonitor — Identificação com Aprendizado por Aliases V24

Esta versão evolui a fila de qualificação de marcas criada na V23.

## Objetivo

Reduzir o volume de `Pendente de identificação`/`Não identificado` no Intel de Mercado sem mascarar a qualidade da base. A V24 transforma a qualificação manual em aprendizado operacional: quando uma marca é confirmada, o sistema pode criar um alias e reaplicar esse alias aos demais itens pendentes.

## Novidades

### Backend

Novas rotas:

- `GET /identification/quality/{project_id}`  
  Retorna qualidade da base, taxa identificada, pendentes, investimento pendente, qualificados e auditáveis pendentes.

- `GET /identification/actions/{project_id}`  
  Retorna a trilha recente de ações de qualificação, ignorados e qualificações automáticas.

- `POST /identification/reprocess-aliases/{project_id}`  
  Reaplica aliases cadastrados sobre os pendentes de identificação.

Rota atualizada:

- `POST /identification/qualify/{project_id}`  
  Agora aceita `apply_alias_to_pending`. Quando verdadeiro, após qualificar o grupo e criar o alias, o sistema tenta qualificar automaticamente outros itens pendentes que contenham o mesmo alias.

### Frontend

Tela atualizada:

- `/admin/identificacao`

Melhorias:

- cards de qualidade da base;
- taxa de identificação;
- quantidade de pendentes;
- investimento pendente;
- sugestões automáticas por alias;
- auditáveis ainda pendentes de identificação;
- botão **Reprocessar aliases**;
- sugestão automática de anunciante quando algum alias já bate com a peça;
- opção **Aplicar alias aos demais pendentes**;
- tabela de últimas ações de identificação.

## Fluxo recomendado

1. Abrir `/admin/identificacao`.
2. Revisar os grupos mais relevantes por investimento.
3. Quando houver sugestão correta, aplicar anunciante.
4. Manter ativo `Criar alias automaticamente`.
5. Ativar `Aplicar alias aos demais pendentes` quando o alias for seguro.
6. Clicar em **Reprocessar aliases** após criar novos aliases.
7. Reabrir `/intel` e gerar os relatórios.

## Resultado esperado

- Menos volume em `Pendente de identificação`.
- Maior taxa de anunciantes identificados.
- Intel de Mercado com rankings mais confiáveis.
- Relatórios comerciais sem tratar pendente como líder de mercado.
- Trilhas de auditoria preservadas.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/admin/identificacao
```
