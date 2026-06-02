# TV Fiscal WebMonitor — V25
## Identificação automática pós-coleta + exportação operacional

Esta versão dá continuidade ao fluxo de qualificação de marcas iniciado nas versões V23/V24.

## Objetivo

Reduzir progressivamente o volume de **Pendente de identificação** no Intel de Mercado, usando os aliases já validados pelo operador em `/admin/identificacao`.

A automação **não inventa marcas**. Ela apenas aplica, após cada coleta, os aliases cadastrados e aprovados anteriormente.

## Principais entregas

### 1. Autoidentificação após scan manual

Ao executar:

```bash
curl -X POST "http://localhost:8000/banners/scan/<PROJECT_ID>?url=https://www.clickpb.com.br&save_rejected=true"
```

O retorno agora inclui:

```json
"identification_auto": {
  "updated": 0,
  "matches": [],
  "message": "..."
}
```

### 2. Autoidentificação após Scheduler

Quando o Scheduler escaneia portais cadastrados, ele passa a executar automaticamente:

```text
coleta dos banners
→ classificação multicamadas
→ salvamento das evidências
→ aplicação de aliases aprendidos
→ snapshot Intel
```

Assim, o Intel já recebe uma base mais qualificada.

### 3. Variável de controle

A automação fica ativada por padrão.

Para desativar:

```env
IDENTIFICATION_AUTO_REPROCESS_AFTER_SCAN=false
```

### 4. Scheduler com resumo de autoidentificação

O retorno da varredura por portais cadastrados passa a incluir:

```json
"auto_identified": 12
```

E o status interno passa a guardar:

```json
"last_identification_at"
"last_identification_summary"
```

### 5. Nova ação administrativa

Nova rota:

```http
POST /identification/auto-run/{project_id}
```

Executa a mesma autoidentificação manualmente e retorna a qualidade da base após o processamento.

### 6. Exportações CSV

Novas rotas:

```http
GET /identification/pending/{project_id}/export.csv
GET /identification/actions/{project_id}/export.csv
```

Servem para auditoria, conferência externa e organização de fila de qualificação.

### 7. Tela /admin/identificacao ajustada

Foram adicionados:

- botão **Autoidentificar agora**;
- botão **Exportar pendentes CSV**;
- botão **Exportar ações CSV**;
- aviso de que aliases aprendidos são aplicados automaticamente ao Scheduler.

## Como aplicar

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Teste recomendado

1. Abrir `/admin/identificacao`.
2. Qualificar alguns grupos pendentes e criar aliases confiáveis.
3. Clicar em **Autoidentificar agora**.
4. Abrir `/intel`.
5. Conferir se caiu o volume de pendentes.
6. Executar `/admin/scheduler` → **Escanear portais cadastrados**.
7. Conferir no retorno do Scheduler o campo `auto_identified`.

## Resultado esperado

O bloco **Pendente de identificação** deixa de crescer sem controle e passa a ser reduzido automaticamente sempre que houver aliases confiáveis cadastrados.
