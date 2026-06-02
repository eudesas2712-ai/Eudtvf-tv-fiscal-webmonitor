# TV Fiscal WebMonitor — Painel Intel + Evidências Operacionais

## Objetivo da entrega

Esta atualização transforma a classificação multicamadas validada em uma camada operacional no frontend e melhora os filtros do backend para consulta de evidências.

## O que foi incluído

### 1. Nova tela operacional

Rota frontend:

```text
/evidencias
```

Arquivo principal:

```text
frontend/src/components/EvidenceConsole.tsx
frontend/src/app/evidencias/page.tsx
```

A tela permite filtrar registros por:

- busca livre;
- finalidade: todos, checking, mercado, notícia, rejeitados;
- portal;
- tipo de conteúdo: publicidade, notícia, misto, institucional, indefinido;
- status de checking: auditável, parcial, revisão, rejeitado;
- score publicitário mínimo;
- score de notícia mínimo;
- apenas itens com evidência preservada.

Também inclui modal de detalhe com:

- preview da evidência;
- OCR;
- motivo técnico da classificação;
- scores;
- links para evidência preservada, imagem original e página original.

### 2. Painel Intel ajustado

Arquivo:

```text
frontend/src/app/intel/page.tsx
```

Ajustes:

- cards separam itens detectados, itens para mercado, publicidade auditável, revisão/parcial e candidatos a notícia;
- histórico de evidências inclui botão para abrir a tela filtrável;
- busca de evidências ampliada para `limit=1000`.

### 3. Painel executivo ajustado

Arquivo:

```text
frontend/src/app/page.tsx
```

Ajustes:

- investimento estimado passa a considerar apenas itens com `market_status = incluido`;
- anunciantes únicos são calculados sobre os itens de inteligência de mercado;
- adicionados atalhos para Evidências Operacionais.

### 4. Menu lateral ajustado

Arquivo:

```text
frontend/src/components/AppShell.tsx
```

Novo item:

```text
Evidências operacionais → /evidencias
```

### 5. Backend com filtros adicionais

Arquivo:

```text
backend/app/routers/banners.py
```

O endpoint abaixo agora aceita filtros adicionais:

```text
GET /banners/{project_id}
```

Novos parâmetros:

```text
usage_scope=checking|market|news
content_type=advertising|news|mixed|institutional|unknown
checking_status=auditavel|parcial|revisao|rejeitado
market_status=incluido|ignorado
news_status=candidato|ignorado
min_publicity_score=0..100
min_news_score=0..100
preserved_only=true|false
date_from=ISO
date_to=ISO
q=texto livre
limit=1..1000
```

### 6. Resumo Intel com novos totais

Arquivo:

```text
backend/app/routers/market_intelligence.py
```

Novos campos adicionados ao retorno de `/intel/summary/{project_id}`:

```json
{
  "total_detected_items": 0,
  "total_market_items": 0,
  "total_checking_ready": 0,
  "total_checking_review": 0,
  "total_checking_rejected": 0,
  "total_news_candidates": 0,
  "total_preserved_evidence": 0
}
```

## Como aplicar

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois, se necessário, reclassificar base existente:

```bash
docker compose exec backend python -m app.scripts.reclassify_banner_items
```

## Testes recomendados

### Intel

```text
http://localhost:3000/intel
```

### Evidências operacionais

```text
http://localhost:3000/evidencias
```

### API filtrada

```bash
curl "http://localhost:8000/banners/9b972aa2-f8a4-483b-a7d1-e979d86482fb?usage_scope=checking&limit=50"

curl "http://localhost:8000/banners/9b972aa2-f8a4-483b-a7d1-e979d86482fb?news_status=candidato&limit=50"

curl "http://localhost:8000/banners/9b972aa2-f8a4-483b-a7d1-e979d86482fb?market_status=incluido&limit=50"
```

## Validação técnica realizada

O backend foi validado com:

```bash
python -m py_compile $(find backend/app -name '*.py')
```

O build Next.js não foi executado neste ambiente porque o pacote enviado não contém `node_modules` e o comando `next` não está instalado localmente fora do container.
