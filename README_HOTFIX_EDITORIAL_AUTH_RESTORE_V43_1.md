# TV Fiscal WebMonitor — Hotfix Editorial Auth/Restore V43.1

## Objetivo

Corrigir o carregamento da tela `/editorial` depois da ativação das permissões finas e da restauração do banco em volume Docker nomeado.

## Diagnóstico

As rotas backend editoriais foram validadas com sucesso via `X-Admin-Token`:

- `GET /editorial/summary/{project_id}` retornou HTTP 200.
- `GET /editorial/items/{project_id}` retornou HTTP 200.

Logo, o problema estava no frontend: o componente `EditorialConsole` ainda fazia chamadas diretas sem anexar a sessão `Authorization: Bearer` nem o token administrativo salvo. Em navegadores, esse cenário podia aparecer como `Failed to fetch` após a V42.

## Ajustes

Arquivo alterado:

- `frontend/src/components/EditorialConsole.tsx`

Correções aplicadas:

1. Adicionado envio automático de `Authorization: Bearer <token>`.
2. Mantida compatibilidade com `X-Admin-Token` salvo no navegador.
3. `NEXT_PUBLIC_API_BASE` passa a ser respeitado antes de `NEXT_PUBLIC_API_URL`.
4. Carregamento de itens editoriais limitado a 80 itens por padrão para reduzir payload inicial.
5. Relatórios PDF agora são baixados por `fetch` autenticado, em vez de link direto sem token.
6. Mensagens de erro mais claras quando backend ou permissão falharem.

## Aplicação

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.backup-volume.override.yml \
  -f docker-compose.local-postgres.override.yml \
  up -d --build --force-recreate backend frontend
```

## Validação

1. Entrar como Administrador.
2. Abrir `/editorial`.
3. Confirmar KPIs: Matérias, Termos, Fontes e Temas.
4. Clicar em `Aplicar filtros`.
5. Gerar `Sintético executivo` e `Analítico expandido`.
6. Testar usuário sem permissão editorial e confirmar bloqueio.
