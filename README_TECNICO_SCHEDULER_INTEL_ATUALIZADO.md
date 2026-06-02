# README Técnico — Operação do Módulo Scheduler/Intel

**Projeto:** TV Fiscal WebMonitor  
**Módulos cobertos:** Intel Dashboard, Histórico Temporal, Scheduler de Snapshots, Painel Administrativo, Autenticação Administrativa, Exportação de Histórico  
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
- permitir execução manual, ativação/desativação, filtros, limpeza e exportação CSV;
- proteger a área administrativa com token.

---

## 2. Rotas Principais

### 2.1 Frontend

```text
http://localhost:3000
http://localhost:3000/intel
http://localhost:3000/admin/scheduler
```

### 2.2 Backend — Intel

```text
GET /intel/summary/{project_id}
GET /intel/timeline/{project_id}
GET /intel/report/pptx/{project_id}
```

### 2.3 Backend — Scheduler Administrativo

```text
GET    /admin/scheduler/status
POST   /admin/scheduler/run-now
POST   /admin/scheduler/enable
POST   /admin/scheduler/disable
GET    /admin/scheduler/history
DELETE /admin/scheduler/history
GET    /admin/scheduler/history/export.csv
```

Todas as rotas `/admin/scheduler/*` estão protegidas por token administrativo.

---

## 3. Autenticação Administrativa

### 3.1 Backend

O backend exige o token em uma das duas formas:

```text
Header: X-Admin-Token
```

ou, para download CSV via navegador:

```text
Query string: ?admin_token=
```

### 3.2 Arquivo responsável

```text
backend/app/core/admin_auth.py
```

### 3.3 Variável de ambiente

No `.env`:

```env
ADMIN_PANEL_TOKEN=tvfiscal-admin-2026
```

Para produção, recomenda-se trocar por um token forte.

### 3.4 Testar sem token

```bash
curl -i http://localhost:8000/admin/scheduler/status
```

Resultado esperado:

```text
401 Unauthorized
```

### 3.5 Testar com token

```bash
curl -i -H "X-Admin-Token: tvfiscal-admin-2026" http://localhost:8000/admin/scheduler/status
```

Resultado esperado:

```text
200 OK
```

### 3.6 CSV protegido

Como `window.open()` não envia headers, o CSV usa `admin_token` na URL:

```text
http://localhost:8000/admin/scheduler/history/export.csv?admin_token=tvfiscal-admin-2026
```

---

## 4. Painel Administrativo do Scheduler

Acesse:

```text
http://localhost:3000/admin/scheduler
```

Fluxo atual:

1. O painel exibe tela de login administrativo.
2. O usuário informa o token.
3. O token é salvo no `localStorage`.
4. Todas as chamadas administrativas enviam `X-Admin-Token`.
5. O botão **Sair** remove o token salvo.
6. O menu lateral identifica a área como administrativa.

---

## 5. Project ID Ativo

```text
9b972aa2-f8a4-483b-a7d1-e979d86482fb
```

---

## 6. Arquivos Principais

### Backend

```text
backend/app/core/admin_auth.py
backend/app/routers/market_intelligence.py
backend/app/routers/scheduler_admin.py
backend/app/services/snapshot_scheduler.py
backend/app/services/snapshot_service.py
backend/app/services/timeline_analyzer.py
backend/app/services/ppt_generator.py
backend/app/main.py
```

### Frontend

```text
frontend/src/app/page.tsx
frontend/src/app/intel/page.tsx
frontend/src/app/admin/scheduler/page.tsx
frontend/src/components/AppShell.tsx
frontend/public/logo-tv-fiscal-clean.png
```

---

## 7. Banco de Dados

### 7.1 `market_snapshots`

```sql
CREATE TABLE IF NOT EXISTS market_snapshots (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    project_id UUID NOT NULL,
    snapshot_data JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);
```

### 7.2 `scheduler_runs`

```sql
CREATE TABLE IF NOT EXISTS scheduler_runs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    project_id UUID,
    status VARCHAR(20) NOT NULL,
    message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 8. Variáveis de Ambiente

```env
SNAPSHOT_SCHEDULER_ENABLED=true
SNAPSHOT_INTERVAL_SECONDS=3600
SNAPSHOT_STARTUP_DELAY_SECONDS=15
SNAPSHOT_PROJECT_IDS=9b972aa2-f8a4-483b-a7d1-e979d86482fb
SNAPSHOT_API_BASE_URL=http://127.0.0.1:8000
ADMIN_PANEL_TOKEN=tvfiscal-admin-2026
```

---

## 9. Comandos Corretos de Rebuild

### 9.1 Alteração apenas no frontend

```bash
docker compose up -d --build --force-recreate frontend
```

### 9.2 Alteração apenas no backend

```bash
python3 -m py_compile backend/app/core/admin_auth.py
python3 -m py_compile backend/app/services/snapshot_scheduler.py
python3 -m py_compile backend/app/routers/scheduler_admin.py
python3 -m py_compile backend/app/routers/market_intelligence.py
docker compose up -d --build --force-recreate backend
```

### 9.3 Alteração em backend e frontend

```bash
docker compose up -d --build --force-recreate backend frontend
```

### 9.4 Reset completo

```bash
docker compose down
docker compose up -d --build
```

### 9.5 Evitar neste projeto

Evite usar isoladamente:

```bash
docker compose exec frontend rm -rf .next
docker compose restart frontend
```

Esse fluxo pode causar 404 temporário em rotas Next.js App Router dentro do Docker.

---

## 10. Testes Operacionais

### Scheduler status protegido

```bash
curl -H "X-Admin-Token: tvfiscal-admin-2026" http://localhost:8000/admin/scheduler/status
```

### Executar coleta manual

```bash
curl -X POST -H "X-Admin-Token: tvfiscal-admin-2026" http://localhost:8000/admin/scheduler/run-now
```

### Listar histórico

```bash
curl -H "X-Admin-Token: tvfiscal-admin-2026" "http://localhost:8000/admin/scheduler/history?limit=20"
```

### Filtrar sucessos

```bash
curl -H "X-Admin-Token: tvfiscal-admin-2026" "http://localhost:8000/admin/scheduler/history?status=success&limit=20"
```

### Limpar apenas erros

```bash
curl -X DELETE -H "X-Admin-Token: tvfiscal-admin-2026" "http://localhost:8000/admin/scheduler/history?status=error"
```

### Exportar CSV

```text
http://localhost:8000/admin/scheduler/history/export.csv?admin_token=tvfiscal-admin-2026
```

---

## 11. Testes do Intel

```text
http://localhost:8000/intel/summary/9b972aa2-f8a4-483b-a7d1-e979d86482fb
http://localhost:8000/intel/timeline/9b972aa2-f8a4-483b-a7d1-e979d86482fb
http://localhost:8000/intel/report/pptx/9b972aa2-f8a4-483b-a7d1-e979d86482fb
```

Frontend:

```text
http://localhost:3000/intel
```

---

## 12. Troubleshooting

### 12.1 Frontend 404 após alteração

Usar:

```bash
docker compose up -d --build --force-recreate frontend
```

Se persistir:

```bash
docker compose down
docker compose up -d --build frontend
```

### 12.2 Scheduler retorna 401

Verificar:

- `.env` contém `ADMIN_PANEL_TOKEN`;
- frontend está enviando `X-Admin-Token`;
- token digitado no painel está correto;
- para CSV, a URL contém `admin_token`.

### 12.3 CSV não baixa

Testar direto:

```text
http://localhost:8000/admin/scheduler/history/export.csv?admin_token=tvfiscal-admin-2026
```

### 12.4 Logo invisível

A logo correta é:

```text
frontend/public/logo-tv-fiscal-clean.png
```

No código:

```tsx
src="/logo-tv-fiscal-clean.png"
```

Não usar:

```tsx
src="/logo-tv-fiscal.png"
```

---

## 13. Estado Atual do Módulo

```text
Intel Dashboard: OK
PPTX Premium: OK
Histórico Temporal: OK
Tendências Competitivas: OK
Scheduler Automático: OK
Painel Admin Scheduler: OK
Histórico Persistente: OK
CSV: OK
Token Admin Backend: OK
Login/Logout Frontend: OK
Menu/Home: OK
Logo/Layout: OK
Docker local: OK
```

---

## 14. Próximas Evoluções Recomendadas

1. Trocar token fixo por usuário/senha com sessão.
2. Criar tela de gerenciamento do token.
3. Adicionar alteração do intervalo do scheduler pela interface.
4. Adicionar seleção dinâmica de project IDs monitorados.
5. Criar gráficos de sucesso/erro do scheduler.
6. Exportar histórico em Excel.
7. Enviar e-mail em caso de erro no scheduler.
8. Criar health check geral do sistema.
9. Criar rotina de backup automático das tabelas.
10. Preparar deploy em VPS com Nginx, domínio e SSL.
