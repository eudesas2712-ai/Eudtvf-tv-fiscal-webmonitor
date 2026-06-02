# TV Fiscal WebMonitor — Scheduler por Portais Cadastrados

## Objetivo

Esta atualização faz o Scheduler usar os cadastros operacionais do WebMonitor como fonte oficial de coleta.

Antes, o fluxo dependia de `SNAPSHOT_PROJECT_IDS` e coletas manuais por URL. Agora o sistema consegue usar:

- projetos cadastrados;
- portais vinculados ao projeto;
- status ativo/inativo dos portais;
- execução manual de varredura por todos os portais cadastrados;
- varredura automática dos portais pelo scheduler.

## Novidades de backend

### Endpoint novo

```text
POST /admin/scheduler/run-portal-scan-now
```

Parâmetros:

```text
project_id      opcional — se omitido, executa todos os projetos configurados
save_rejected   opcional — padrão true, preserva rejeitados para mercado/notícia
```

Exemplo:

```bash
curl -X POST \
  -H "X-Admin-Token: tvfiscal-admin-2026" \
  "http://localhost:8000/admin/scheduler/run-portal-scan-now?save_rejected=true"
```

### Status ampliado

`GET /admin/scheduler/status` agora retorna também:

```text
configured_projects
configured_portal_count
scan_registered_portals
use_registered_projects
scan_count
last_scan_at
last_portal_url
last_scan_summary
```

## Variáveis de ambiente novas

```env
SNAPSHOT_USE_REGISTERED_PROJECTS=true
SNAPSHOT_SCAN_REGISTERED_PORTALS=true
```

Com `SNAPSHOT_USE_REGISTERED_PROJECTS=true`, o scheduler prioriza projetos que tenham portais ativos vinculados em `/admin/cadastros`.

Se nenhum vínculo existir, o sistema mantém compatibilidade e usa `SNAPSHOT_PROJECT_IDS`.

Com `SNAPSHOT_SCAN_REGISTERED_PORTALS=true`, cada ciclo do scheduler:

1. escaneia os portais ativos vinculados ao projeto;
2. salva todos os detectados com classificação multicamadas;
3. atualiza o snapshot Intel do projeto.

## Novidades no painel admin

Em:

```text
http://localhost:3000/admin/scheduler
```

Foram adicionados:

- card de varreduras de portais;
- informação de última varredura;
- último portal escaneado;
- origem dos projetos monitorados;
- lista de projetos e portais cadastrados;
- resumo da última varredura;
- botão **Escanear portais cadastrados**.

## Fluxo operacional recomendado

1. Abrir `/admin/cadastros`.
2. Criar ou conferir portais.
3. Vincular portais ao projeto ativo.
4. Abrir `/admin/scheduler`.
5. Confirmar se os portais aparecem em “Projetos e portais cadastrados”.
6. Clicar em **Escanear portais cadastrados**.
7. Conferir `/evidencias`, `/intel` e `/intel/comparativo`.

## Comando de rebuild

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Validação técnica

Foram compilados com sucesso:

```bash
python3 -m py_compile backend/app/services/snapshot_scheduler.py
python3 -m py_compile backend/app/routers/scheduler_admin.py
python3 -m py_compile backend/app/routers/registry.py
python3 -m py_compile backend/app/routers/banners.py
```
