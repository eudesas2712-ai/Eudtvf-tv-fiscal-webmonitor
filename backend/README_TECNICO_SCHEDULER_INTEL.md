# README Técnico — Operação do Módulo Scheduler/Intel

**Projeto:** TV Fiscal WebMonitor  
**Módulos cobertos:** Intel Dashboard, Histórico Temporal, Scheduler de Snapshots, Painel Administrativo, Exportação de Histórico  
**Ambiente:** Docker + FastAPI + Next.js + PostgreSQL  
**Última atualização:** 27/05/2026

---

## 1. Visão Geral

O módulo **Intel/Scheduler** é responsável por:

- gerar inteligência de mercado publicitário;
- salvar snapshots automáticos do cenário monitorado;
- comparar evolução temporal entre snapshots;
- alimentar o dashboard `/intel`;
- gerar relatórios PPTX premium;
- administrar coletas automáticas via `/admin/scheduler`;
- persistir histórico de coletas no PostgreSQL;
- permitir execução manual, ativação/desativação, filtros, limpeza e exportação CSV.

---

## 2. Principais Rotas

### 2.1 Dashboard Intel

Frontend:

```text
http://localhost:3000/intel
```

Backend:

```text
http://localhost:8000/intel/summary/{project_id}
http://localhost:8000/intel/timeline/{project_id}
http://localhost:8000/intel/report/pptx/{project_id}
```

Projeto padrão utilizado:

```text
9b972aa2-f8a4-483b-a7d1-e979d86482fb
```

---

### 2.2 Painel Administrativo do Scheduler

Frontend:

```text
http://localhost:3000/admin/scheduler
```

Backend:

```text
http://localhost:8000/admin/scheduler/status
http://localhost:8000/admin/scheduler/history
http://localhost:8000/admin/scheduler/history/export.csv
```

Ações administrativas:

```text
POST   /admin/scheduler/run-now
POST   /admin/scheduler/enable
POST   /admin/scheduler/disable
DELETE /admin/scheduler/history
```

---

## 3. Arquivos Principais

### Backend

```text
backend/app/services/snapshot_scheduler.py
backend/app/services/snapshot_service.py
backend/app/services/timeline_analyzer.py
backend/app/services/ppt_generator.py
backend/app/routers/scheduler_admin.py
backend/app/routers/market_intelligence.py
backend/app/main.py
```

### Frontend

```text
frontend/src/app/intel/page.tsx
frontend/src/app/admin/scheduler/page.tsx
```

### Banco de Dados

```text
market_snapshots
scheduler_runs
```

---

## 4. Tabelas PostgreSQL

### 4.1 Tabela de snapshots de mercado

```sql
CREATE TABLE IF NOT EXISTS market_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    project_id UUID NOT NULL,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Essa tabela guarda os snapshots de inteligência de mercado usados pelo histórico temporal.

---

### 4.2 Tabela de histórico do scheduler

```sql
CREATE TABLE IF NOT EXISTS scheduler_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    project_id UUID,
    status VARCHAR(20) NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

Essa tabela registra cada execução automática ou manual do scheduler.

---

## 5. Variáveis de Ambiente

No arquivo `.env`, manter:

```env
SNAPSHOT_SCHEDULER_ENABLED=true
SNAPSHOT_INTERVAL_SECONDS=3600
SNAPSHOT_STARTUP_DELAY_SECONDS=15
SNAPSHOT_PROJECT_IDS=9b972aa2-f8a4-483b-a7d1-e979d86482fb
SNAPSHOT_API_BASE_URL=http://127.0.0.1:8000
```

### Significado

| Variável | Função |
|---|---|
| `SNAPSHOT_SCHEDULER_ENABLED` | Ativa/desativa o scheduler no startup |
| `SNAPSHOT_INTERVAL_SECONDS` | Intervalo entre coletas automáticas |
| `SNAPSHOT_STARTUP_DELAY_SECONDS` | Espera inicial após subir o backend |
| `SNAPSHOT_PROJECT_IDS` | Lista de projetos monitorados |
| `SNAPSHOT_API_BASE_URL` | URL interna usada pelo scheduler |

Para teste rápido:

```env
SNAPSHOT_INTERVAL_SECONDS=60
SNAPSHOT_STARTUP_DELAY_SECONDS=5
```

Para produção local:

```env
SNAPSHOT_INTERVAL_SECONDS=3600
SNAPSHOT_STARTUP_DELAY_SECONDS=15
```

---

## 6. Comandos de Operação

### 6.1 Ver containers ativos

```bash
docker compose ps
```

### 6.2 Ver logs do backend

```bash
docker compose logs --tail=80 backend
```

### 6.3 Ver logs do frontend

```bash
docker compose logs --tail=80 frontend
```

---

## 7. Procedimento Correto de Rebuild

### 7.1 Quando alterar apenas frontend

Usar:

```bash
docker compose up -d --build --force-recreate frontend
```

Evitar usar apenas:

```bash
docker compose exec frontend rm -rf .next
docker compose restart frontend
```

Motivo: no Next.js App Router dentro do Docker, limpar `.next` e apenas reiniciar pode gerar erro 404 temporário nas rotas.

---

### 7.2 Quando alterar apenas backend

Validar sintaxe dos arquivos alterados:

```bash
python3 -m py_compile backend/app/services/snapshot_scheduler.py
python3 -m py_compile backend/app/routers/scheduler_admin.py
python3 -m py_compile backend/app/routers/market_intelligence.py
```

Subir backend:

```bash
docker compose up -d --build --force-recreate backend
```

---

### 7.3 Quando alterar backend e frontend

```bash
docker compose up -d --build --force-recreate backend frontend
```

---

### 7.4 Reset completo em caso de erro persistente

```bash
docker compose down
docker compose up -d --build
```

Ou separadamente:

```bash
docker compose down
docker compose up -d --build backend
docker compose up -d --build frontend
```

---

## 8. Testes do Scheduler

### 8.1 Status

```bash
curl http://localhost:8000/admin/scheduler/status
```

Retorno esperado:

```json
{
  "enabled": true,
  "running": true,
  "run_count": 1,
  "project_ids": ["9b972aa2-f8a4-483b-a7d1-e979d86482fb"]
}
```

---

### 8.2 Executar coleta manual

```bash
curl -X POST http://localhost:8000/admin/scheduler/run-now
```

Retorno esperado:

```json
{
  "executed": true,
  "results": [
    {
      "success": true
    }
  ]
}
```

---

### 8.3 Desativar scheduler

```bash
curl -X POST http://localhost:8000/admin/scheduler/disable
```

### 8.4 Ativar scheduler

```bash
curl -X POST http://localhost:8000/admin/scheduler/enable
```

---

## 9. Histórico do Scheduler

### 9.1 Listar histórico

```bash
curl "http://localhost:8000/admin/scheduler/history?limit=20"
```

### 9.2 Filtrar sucessos

```bash
curl "http://localhost:8000/admin/scheduler/history?status=success&limit=20"
```

### 9.3 Filtrar erros

```bash
curl "http://localhost:8000/admin/scheduler/history?status=error&limit=20"
```

### 9.4 Limpar apenas erros

```bash
curl -X DELETE "http://localhost:8000/admin/scheduler/history?status=error"
```

### 9.5 Limpar todo o histórico

```bash
curl -X DELETE "http://localhost:8000/admin/scheduler/history"
```

### 9.6 Exportar CSV

```text
http://localhost:8000/admin/scheduler/history/export.csv
```

Com filtro:

```text
http://localhost:8000/admin/scheduler/history/export.csv?status=success&limit=100
```

---

## 10. Testes do Intel

### 10.1 Summary

```text
http://localhost:8000/intel/summary/9b972aa2-f8a4-483b-a7d1-e979d86482fb
```

### 10.2 Timeline

```text
http://localhost:8000/intel/timeline/9b972aa2-f8a4-483b-a7d1-e979d86482fb
```

Retorno esperado:

```json
{
  "project_id": "...",
  "points": [],
  "analysis": {
    "has_comparison": true,
    "insights": []
  }
}
```

### 10.3 Relatório PPTX

```text
http://localhost:8000/intel/report/pptx/9b972aa2-f8a4-483b-a7d1-e979d86482fb
```

O relatório deve conter:

- Resumo Executivo;
- Market Snapshot;
- Diagnóstico Executivo;
- Top Anunciantes;
- Top Portais;
- Segmentos de Mercado;
- Mapa Competitivo;
- Pressão Competitiva por Portal;
- Estrutura Competitiva;
- Dependência por Portal;
- Insights e Alertas;
- Recomendações Estratégicas;
- Tendências Competitivas;
- Histórico Temporal.

---

## 11. Troubleshooting

### 11.1 Página frontend retorna 404

Causa provável:
- cache/rota do Next.js não recompilada corretamente;
- arquivo fora do caminho correto;
- container antigo servindo rota anterior.

Verificar caminho:

```bash
ls -la frontend/src/app/admin/scheduler/page.tsx
docker compose exec frontend sh -lc "ls -la /app/src/app/admin/scheduler/page.tsx"
```

Corrigir com:

```bash
docker compose up -d --build --force-recreate frontend
```

Se persistir:

```bash
docker compose down
docker compose up -d --build frontend
```

---

### 11.2 Backend retorna 404 em `/admin/scheduler/history`

Verificar rotas carregadas:

```bash
docker compose exec backend sh -lc "python - <<'PY'
from app.main import app
for r in app.routes:
    path = getattr(r, 'path', '')
    if 'scheduler' in path:
        print(getattr(r, 'methods', None), path)
PY"
```

Rotas esperadas:

```text
/admin/scheduler/status
/admin/scheduler/run-now
/admin/scheduler/enable
/admin/scheduler/disable
/admin/scheduler/history
/admin/scheduler/history/export.csv
```

---

### 11.3 Erro de timezone entre última coleta e histórico

Causa:
- `last_success_at` usa UTC;
- `scheduler_runs.created_at` vem do PostgreSQL;
- browser interpreta timestamps sem timezone de forma diferente.

Correção aplicada no frontend:

```tsx
function fmtDate(value: any) {
  if (!value) return "Não registrado";

  let normalizedValue = String(value);

  const looksLikeIsoWithoutTimezone =
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/.test(normalizedValue) &&
    !normalizedValue.endsWith("Z") &&
    !normalizedValue.includes("+");

  if (looksLikeIsoWithoutTimezone) {
    normalizedValue = `${normalizedValue}Z`;
  }

  const d = new Date(normalizedValue);

  if (Number.isNaN(d.getTime())) {
    return String(value);
  }

  return d.toLocaleString("pt-BR");
}
```

---

### 11.4 Duplicação de snapshots

O backend já possui deduplicação temporal/lógica no `snapshot_service.py`.

Se aparecer duplicação visual:

1. verificar se o frontend não está fazendo múltiplas chamadas;
2. verificar logs do backend;
3. limpar snapshots de teste, se necessário:

```bash
docker compose exec postgres psql -U webmonitor -d webmonitor -c "TRUNCATE TABLE market_snapshots;"
```

---

### 11.5 Erro em imports React/Recharts

Erros comuns:

```text
ReferenceError: useState is not defined
ReferenceError: Legend is not defined
```

Corrigir imports:

```tsx
import { useEffect, useRef, useState } from "react";
```

E, para gráficos:

```tsx
import {
  LineChart,
  Line,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
```

---

## 12. Estado Atual do Módulo

### Intel

- Dashboard funcional.
- KPIs executivos.
- Ranking de anunciantes.
- Ranking de portais.
- Insights automáticos.
- Alertas inteligentes.
- Histórico temporal.
- Gráfico temporal.
- Tendências competitivas.
- Exportação PPTX premium.

### Scheduler

- Coleta automática ativa.
- Execução manual.
- Ativação/desativação pela interface.
- Histórico persistente no PostgreSQL.
- Filtros por status.
- Limpeza de histórico.
- Exportação CSV.
- Página administrativa funcional.

---

## 13. Próximas Evoluções Recomendadas

1. Criar autenticação no painel `/admin/scheduler`.
2. Adicionar seleção dinâmica de projetos monitorados.
3. Permitir alteração do intervalo pela interface.
4. Criar exportação Excel além de CSV.
5. Adicionar indicadores gráficos de sucesso/erro das coletas.
6. Criar alerta por e-mail em caso de erro no scheduler.
7. Integrar o painel admin ao menu principal do WebMonitor.
8. Criar logs estruturados para produção.
9. Criar backup automático das tabelas `market_snapshots` e `scheduler_runs`.
10. Criar página de saúde geral do sistema com backend, frontend, PostgreSQL, Redis, MinIO e OpenSearch.

---

## 14. Checklist Operacional Rápido

Após qualquer alteração:

```bash
docker compose ps
docker compose logs --tail=40 backend
docker compose logs --tail=40 frontend
```

Testes mínimos:

```bash
curl http://localhost:8000/admin/scheduler/status
curl "http://localhost:8000/admin/scheduler/history?limit=10"
curl http://localhost:8000/intel/timeline/9b972aa2-f8a4-483b-a7d1-e979d86482fb
```

Abrir no navegador:

```text
http://localhost:3000/intel
http://localhost:3000/admin/scheduler
```

---

## 15. Comando de Rebuild Recomendado para Manutenção

Frontend:

```bash
docker compose up -d --build --force-recreate frontend
```

Backend:

```bash
docker compose up -d --build --force-recreate backend
```

Ambos:

```bash
docker compose up -d --build --force-recreate backend frontend
```

Reset completo:

```bash
docker compose down
docker compose up -d --build
```
O painel /admin/scheduler está protegido por token administrativo.
O backend exige X-Admin-Token ou admin_token via query string para download CSV.
O frontend exibe tela de acesso administrativo e salva o token temporariamente no localStorage.
O menu identifica a rota como área administrativa.