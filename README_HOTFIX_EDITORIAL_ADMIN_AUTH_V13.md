# TV Fiscal WebMonitor — Hotfix Editorial Admin Auth V13

## Correção

O backend não subia após o módulo editorial porque `backend/app/routers/editorial.py` importava uma função inexistente:

```python
from app.core.admin_auth import require_admin_token
```

No projeto consolidado, a função correta é:

```python
from app.core.admin_auth import require_admin_access
```

## Arquivo ajustado

```text
backend/app/routers/editorial.py
```

## Validação

Compilação Python validada:

```bash
python3 -m py_compile backend/app/routers/editorial.py backend/app/core/admin_auth.py backend/app/main.py backend/app/services/editorial_service.py
```

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Testes

```bash
docker compose ps
docker compose logs backend --tail=120
curl http://localhost:8000/health
```

Depois:

```bash
curl -X POST \
  -H "X-Admin-Token: tvfiscal-admin-2026" \
  "http://localhost:8000/editorial/run/9b972aa2-f8a4-483b-a7d1-e979d86482fb?collect_all=true&limit_per_source=25"
```
