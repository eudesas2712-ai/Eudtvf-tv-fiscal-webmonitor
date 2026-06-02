# TV Fiscal WebMonitor — Hotfix Intel Fast Summary V42.3

## Objetivo
Corrigir travamento da página `/intel` e do endpoint:

```bash
GET /intel/summary/{project_id}
```

Após a V42, o acesso autenticado passou a funcionar, mas o resumo de Inteligência de Mercado podia ficar sem resposta em bases maiores.

## Causa provável
O endpoint antigo carregava todos os `banner_items` do projeto em memória, reprocessava classificação e resolvia aliases item a item. Em bases com muitos registros, isso podia travar o carregamento do painel e deixar o `curl` aguardando indefinidamente.

## Ajuste aplicado
O endpoint `/intel/summary/{project_id}` agora usa uma versão otimizada por consultas SQL agregadas.

A nova versão:

- não carrega todos os banners em memória;
- não executa resolução de alias item a item;
- não salva snapshot durante cada abertura do painel;
- retorna rapidamente KPIs, rankings, portais, confiança e qualidade de identificação;
- mantém os campos esperados pelo frontend e pelos relatórios.

## Arquivo alterado

```text
backend/app/routers/market_intelligence.py
```

## Como aplicar

```bash
docker compose -f docker-compose.yml -f docker-compose.backup-volume.override.yml up -d --build --force-recreate backend frontend
```

## Teste rápido

```bash
curl --max-time 20 -H "X-Admin-Token: tvfiscal-admin-2026" \
"http://localhost:8000/intel/summary/9b972aa2-f8a4-483b-a7d1-e979d86482fb"
```

Depois acessar:

```text
http://localhost:3000/intel
```

## Resultado esperado

- O `curl` responde em poucos segundos.
- A tela `/intel` sai de `Carregando...`.
- KPIs e rankings carregam normalmente.
- PDF/PPTX do Intel continuam disponíveis.

