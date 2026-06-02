# Hotfix V42.1 — Intel com autenticação e downloads protegidos

## Correção

Após a V42, a página `/intel` ainda fazia chamadas diretas ao backend sem enviar o `Authorization: Bearer <token>` da sessão. Em modo de permissões finas, especialmente com `AUTH_ENFORCEMENT_MODE=strict`, isso podia impedir o carregamento da Inteligência de Mercado mesmo para usuário administrador.

## Ajustes aplicados

- `/intel` agora instala o interceptador de autenticação.
- As chamadas do painel Intel passam a usar `Authorization: Bearer`.
- A página foi envolvida no `AppShell`, mantendo sessão, menu e logout.
- Downloads de PDF/PPTX do Intel e Relatório Completo agora usam `fetch` autenticado e baixam o arquivo com blob.
- `frontend/src/lib/api.ts` passou a anexar token de sessão em `apiGet`.

## Arquivos alterados

- `frontend/src/app/intel/page.tsx`
- `frontend/src/lib/api.ts`

## Como aplicar

```bash
docker compose -f docker-compose.yml -f docker-compose.backup-volume.override.yml up -d --build --force-recreate backend frontend
```

## Teste recomendado

1. Entrar como administrador.
2. Abrir `/intel`.
3. Confirmar carregamento dos KPIs.
4. Gerar PDF/PPTX do Intel.
5. Entrar com usuário sem módulo `intel` e confirmar bloqueio.
6. Entrar com usuário com módulo `intel` e confirmar acesso.
