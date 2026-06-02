# Hotfix V6 — Portais padrão vinculados ao projeto ativo

## Problema corrigido

O painel `/admin/scheduler` já estava configurado para usar os portais cadastrados, mas o projeto ativo ainda aparecia com:

```text
Portais cadastrados vinculados: 0
Sem portal ativo vinculado.
```

Com isso, a varredura de portais retornava erro:

```text
Nenhum portal ativo vinculado ao projeto.
```

## O que foi adicionado

### Backend

Nova rota administrativa:

```text
POST /registry/projects/{project_id}/bootstrap-portals
```

Ela cria/reativa e vincula ao projeto ativo os portais padrão:

- ClickPB — https://www.clickpb.com.br
- Jornal da Paraíba — https://www.jornaldaparaiba.com.br
- WSCom — https://www.wscom.com.br
- Portal Correio — https://www.portalcorreio.com.br
- Polêmica Paraíba — https://www.polemicaparaiba.com.br

### Frontend

Foram adicionados botões em:

```text
/admin/scheduler
/admin/cadastros
```

Botão:

```text
Criar/vincular portais padrão
```

## Fluxo recomendado

1. Rebuild do backend e frontend:

```bash
docker compose up -d --build --force-recreate backend frontend
```

2. Acessar:

```text
http://localhost:3000/admin/scheduler
```

3. Clicar em:

```text
Criar/vincular portais padrão
```

4. Confirmar se `Portais cadastrados vinculados` passou de `0` para `5`.

5. Clicar em:

```text
Escanear portais cadastrados
```

6. Conferir os resultados em:

```text
/evidencias
/intel
/intel/comparativo
```

## Observação

Este hotfix não altera a classificação multicamadas. Ele apenas resolve a etapa operacional de vínculo entre projeto e portais cadastrados.
