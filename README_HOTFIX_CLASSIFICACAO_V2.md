# HOTFIX V2 — Classificação Multicamadas / Checking x Mercado x Notícias

## Motivo do hotfix

O teste real no ClickPB indicou que o endpoint `/banners/scan/{project_id}` estava salvando os rejeitados corretamente, mas ainda havia dois problemas:

1. `auditables` podia contar qualquer item com evidência preservada, mesmo quando o item não era publicidade aprovada para checking.
2. Várias imagens editoriais de notícia entravam como candidatas por causa de `+banner_format`, embora o formato sozinho não deva aprovar publicidade.

## Correções principais

- `auditables` agora conta apenas itens com `checking_status = auditavel`.
- `+banner_format` sozinho passa a ser insuficiente para checking.
- Imagens de `/wp-content/uploads/` com ALT/título editorial são classificadas como `news` e `news_status = candidato`.
- Itens comerciais de Hotmart/OEAD, preço, curso, oferta ou CTA entram como publicidade parcial/revisão/auditável conforme score.
- Itens rejeitados continuam sendo salvos quando `save_rejected=true`, mas não entram como publicidade confirmada.
- O retorno do scan passa a separar:
  - `checking.auditavel`
  - `checking.parcial`
  - `checking.revisao`
  - `checking.rejeitado`
  - `market_intelligence.included`
  - `news_monitoring.candidates`

## Como aplicar

Copie as pastas `backend` e `frontend` deste pacote por cima da raiz atual do projeto.

Depois execute:

```bash
docker compose up -d --build --force-recreate backend frontend
```

Reclassifique a base existente:

```bash
docker compose exec backend python -m app.scripts.reclassify_banner_items
```

Teste novamente:

```bash
curl -X POST "http://localhost:8000/banners/scan/9b972aa2-f8a4-483b-a7d1-e979d86482fb?url=https://www.clickpb.com.br&save_rejected=true"
```

## Resultado esperado

O resultado não deve mais mostrar algo contraditório como:

```json
"accepted": 0,
"auditables": 29
```

Se `accepted` for `0`, então `auditables` também deve ser `0`.

Os cards editoriais do portal devem aparecer majoritariamente como:

```json
"content_type": "news",
"checking_status": "rejeitado",
"news_status": "candidato"
```

Os banners/ofertas/infoprodutos devem aparecer como:

```json
"content_type": "advertising",
"checking_status": "parcial" ou "auditavel",
"market_status": "incluido"
```
