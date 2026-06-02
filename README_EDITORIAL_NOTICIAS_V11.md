# TV Fiscal WebMonitor — Módulo Editorial/Notícias V11

Esta versão inicia a frente editorial do WebMonitor, mantendo preservado o módulo publicitário/checking já homologado.

## Novidades

- Nova tela `/editorial`.
- Novo backend `/editorial/*`.
- Coleta editorial por projeto usando portais/fontes vinculados.
- Detecção de termos monitorados e aliases de anunciantes vinculados.
- Tema editorial básico.
- Sentimento básico.
- Score editorial.
- Filtros por fonte, termo, tema, sentimento, busca e período.
- PDF editorial inicial.
- Checkpoint técnico atualizado incluído na raiz do pacote.

## Rotas

```text
GET    /editorial/summary/{project_id}
GET    /editorial/items/{project_id}
POST   /editorial/run/{project_id}
GET    /editorial/report/{project_id}
GET    /editorial/report-pdf/{project_id}
DELETE /editorial/clear/{project_id}
```

## Como aplicar

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Como testar

Acesse:

```text
http://localhost:3000/editorial
```

Execute a coleta pela própria tela ou via curl:

```bash
curl -X POST \
  -H "X-Admin-Token: tvfiscal-admin-2026" \
  "http://localhost:8000/editorial/run/9b972aa2-f8a4-483b-a7d1-e979d86482fb?collect_all=true&limit_per_source=25"
```

Depois confira:

```text
http://localhost:8000/editorial/items/9b972aa2-f8a4-483b-a7d1-e979d86482fb
http://localhost:8000/editorial/report-pdf/9b972aa2-f8a4-483b-a7d1-e979d86482fb
```
