# Hotfix V12 — Backend editorial não sobe / Failed to fetch

Este hotfix remove a dependência de importação direta do WeasyPrint no módulo editorial.

## Problema observado

- Tela `/editorial` abria, mas exibiu `Failed to fetch`.
- `curl http://localhost:8000/...` retornou `Couldn't connect to server`.
- Isso indica backend parado ou falha de inicialização do container.

## Correção

- `backend/app/routers/editorial.py` não importa mais `weasyprint` no startup.
- O PDF editorial agora é gerado com ReportLab, já usado nos relatórios comparativos e por projeto.
- A tela editorial mostra mensagem mais clara quando não consegue conectar no backend.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Verificação

```bash
docker compose ps
docker compose logs backend --tail=120
curl http://localhost:8000/health
```

## Teste editorial

```bash
curl -X POST \
  -H "X-Admin-Token: tvfiscal-admin-2026" \
  "http://localhost:8000/editorial/run/9b972aa2-f8a4-483b-a7d1-e979d86482fb?collect_all=true&limit_per_source=25"
```
