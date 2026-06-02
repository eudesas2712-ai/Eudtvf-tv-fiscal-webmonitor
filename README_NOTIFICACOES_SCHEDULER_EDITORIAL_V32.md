# TV Fiscal WebMonitor — V32
## Disparo automático integrado ao Scheduler e à coleta editorial

Esta versão fecha o fluxo operacional do Motor de Notificações: os alertas deixam de depender do botão **Avaliar regras e enviar agora** e passam a ser avaliados automaticamente após as coletas.

## O que foi implementado

1. **Avaliação automática após coleta editorial**
   - Ao executar `POST /editorial/run/{project_id}`, o sistema coleta matérias, classifica o conteúdo editorial e aciona o motor de regras.
   - Se houver termo, marca, personalidade ou regra sensível cadastrada, o sistema registra/envia notificações automaticamente.

2. **Avaliação automática após Scheduler / varredura de portais**
   - Ao executar o Scheduler ou `POST /admin/scheduler/run-portal-scan-now`, o sistema realiza scan, aplica autoidentificação por alias e avalia as regras de notificação.
   - Quando o e-mail automático por projeto estiver salvo, o canal e-mail envia de forma real pelo SMTP homologado.

3. **Janela de eventos recentes**
   - Para evitar disparo massivo de clipping antigo, a automação usa uma janela curta de eventos recentes.
   - Variáveis configuráveis:

```env
NOTIFICATIONS_AUTO_EVALUATE_AFTER_EDITORIAL=true
NOTIFICATIONS_AUTO_EVALUATE_AFTER_SCHEDULER=true
NOTIFICATIONS_AUTO_EVENT_WINDOW_MINUTES=180
NOTIFICATIONS_AUTO_EVENT_LIMIT=120
```

4. **Log das execuções automáticas**
   - Nova tabela: `notification_automation_runs`.
   - Ela registra:
     - origem do disparo;
     - quantidade de eventos avaliados;
     - notificações geradas;
     - e-mails enviados;
     - duplicidades ignoradas;
     - erros.

5. **Novas rotas**

```text
POST /notifications/automation-test/{project_id}
GET  /notifications/automation-runs/{project_id}
```

6. **Tela /admin/notifications atualizada**
   - Novo bloco: **Automação pós-coleta**.
   - Mostra status da automação editorial e scheduler.
   - Mostra últimas execuções automáticas.
   - Inclui botão: **Testar fluxo automático**.

## Fluxo final

```text
Scheduler / Coleta editorial
→ Classificação editorial/publicitária
→ Central de Alertas
→ Motor de regras
→ E-mail real automático quando configurado
→ Log de notificação
→ Log de execução automática
```

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Teste recomendado

1. Abrir `/admin/notifications`.
2. Confirmar SMTP automático ativo.
3. Confirmar regras ativas.
4. Clicar em **Testar fluxo automático**.
5. Rodar coleta editorial:

```bash
curl -X POST \
  -H "X-Admin-Token: tvfiscal-admin-2026" \
  "http://localhost:8000/editorial/run/9b972aa2-f8a4-483b-a7d1-e979d86482fb?collect_all=true&limit_per_source=25"
```

6. Conferir logs em `/admin/notifications`.
7. Rodar Scheduler manual:

```bash
curl -X POST \
  -H "X-Admin-Token: tvfiscal-admin-2026" \
  "http://localhost:8000/admin/scheduler/run-portal-scan-now?project_id=9b972aa2-f8a4-483b-a7d1-e979d86482fb"
```

8. Conferir se a execução automática ficou registrada.

## Segurança operacional

- SMS e WhatsApp continuam dependentes de provedor real.
- E-mail automático usa o SMTP salvo por projeto.
- O cooldown das regras continua evitando alertas repetidos.
- A automação avalia apenas uma janela recente, evitando disparos sobre todo o histórico.
