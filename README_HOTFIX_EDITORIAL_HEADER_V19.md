# TV Fiscal WebMonitor — Hotfix Editorial Header V19

## Ajuste aplicado

Corrige definitivamente o cabeçalho dos relatórios editoriais premium.

### Antes
O cabeçalho mantinha o bloco `RISCO / Alto` ao lado da logomarca. Mesmo separado visualmente, isso ainda gerava confusão e parecia texto deslocado na área da logo.

### Agora
O cabeçalho exibe apenas:

- título do relatório;
- subtítulo;
- projeto/cliente;
- logomarca TV Fiscal isolada em bloco branco no canto direito.

O risco reputacional permanece somente na linha de KPIs, onde faz sentido analítico.

## Arquivo alterado

```text
backend/app/services/editorial_report_generator.py
```

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois gere novamente em `/editorial`:

- Sintético executivo
- Analítico expandido
