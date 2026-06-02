# TV Fiscal WebMonitor — V36
## Relatório Gerencial de Alertas e SLA

Esta versão adiciona uma visão executiva para acompanhamento da operação de alertas, produtividade, SLA, responsáveis e canais de notificação.

## Nova tela

```text
/alerts/reports
```

## Recursos implementados

```text
1. Dashboard gerencial de alertas por projeto
2. Filtros por período
3. KPIs operacionais:
   - total de alertas
   - alertas ativos
   - resolvidos
   - vencidos
   - sem responsável
   - erros de envio
   - tempo médio até ciência
   - tempo médio até resolução
4. Rankings:
   - por responsável
   - por severidade
   - por canal
   - por status operacional
   - por categoria
   - reincidência de termos/temas
5. Fila crítica de SLA
6. Exportação em CSV
7. Relatório PDF premium
8. Relatório PPTX executivo
9. Menu lateral atualizado
```

## Novas rotas backend

```text
GET /notifications/reports/alerts/{project_id}
GET /notifications/reports/alerts/{project_id}/export.csv
GET /notifications/reports/alerts/{project_id}/pdf
GET /notifications/reports/alerts/{project_id}/pptx
```

Parâmetros opcionais:

```text
start_date=YYYY-MM-DD
end_date=YYYY-MM-DD
```

Exemplos:

```bash
curl "http://localhost:8000/notifications/reports/alerts/9b972aa2-f8a4-483b-a7d1-e979d86482fb"

curl "http://localhost:8000/notifications/reports/alerts/9b972aa2-f8a4-483b-a7d1-e979d86482fb/pdf?start_date=2026-05-01&end_date=2026-05-29"
```

## Arquivos alterados/adicionados

```text
backend/app/services/notification_report_service.py
backend/app/routers/notifications.py
backend/app/core/bootstrap.py
frontend/src/app/alerts/reports/page.tsx
frontend/src/components/AppShell.tsx
```

## Observação técnica

Também foi corrigida a chamada de bootstrap das tabelas de automação/SLA para garantir que `ensure_notification_automation_runs(engine)` e `ensure_notification_sla_columns(engine)` sejam executadas separadamente.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/alerts/reports
```
