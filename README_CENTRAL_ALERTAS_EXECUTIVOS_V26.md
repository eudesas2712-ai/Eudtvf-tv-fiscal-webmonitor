# TV Fiscal WebMonitor — Central de Alertas Executivos V26

## Objetivo

Esta versão adiciona uma central executiva de alertas para consolidar riscos e prioridades operacionais do projeto monitorado.

A central reúne alertas de:

- identificação comercial pendente;
- checking publicitário;
- baixa confiança de classificação;
- concentração de mercado por portal;
- candidatos editoriais separados da publicidade;
- clipping editorial negativo;
- termos/marcas detectados em notícias.

## Nova tela

```text
/alerts
```

## Novas rotas backend

```text
GET /alerts/summary/{project_id}
GET /alerts/summary/{project_id}/export.csv
```

## Arquivos principais

```text
backend/app/services/alerts_service.py
backend/app/routers/alerts.py
backend/app/main.py
frontend/src/app/alerts/page.tsx
frontend/src/components/AppShell.tsx
```

## O que a central mostra

- total de alertas;
- críticos/altos;
- pendentes de identificação;
- investimento pendente de identificação;
- peças auditáveis;
- taxa de baixa confiança;
- matérias editoriais;
- matérias negativas;
- alertas priorizados por score;
- ação recomendada por alerta;
- atalho para tela correspondente;
- leitura de mercado;
- leitura editorial;
- exportação CSV.

## Fluxo operacional recomendado

1. Abrir `/alerts`.
2. Revisar alertas críticos/altos.
3. Resolver primeiro pendentes de identificação em `/admin/identificacao`.
4. Revisar itens auditáveis e revisão/parcial em `/evidencias`.
5. Revisar matérias negativas em `/editorial`.
6. Reabrir `/intel` e gerar relatórios atualizados.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acessar:

```text
http://localhost:3000/alerts
```
