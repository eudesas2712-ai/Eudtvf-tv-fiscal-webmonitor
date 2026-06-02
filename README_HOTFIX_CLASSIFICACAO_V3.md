# HOTFIX CLASSIFICAÇÃO MULTICAMADAS V3 — TV Fiscal WebMonitor

## Motivo

O teste real no ClickPB após a V2 mostrou que o resumo geral ficou coerente (`accepted=5` e `auditables=5`), porém algumas notícias com valores monetários estavam entrando como `Misto/revisao` por conterem termos como `R$`, `desconto`, `licitação` ou `gasolina`.

Exemplos que devem ser notícia, não revisão publicitária:

- Petrobras anuncia aumento de R$ 0,48 na gasolina para distribuidoras;
- Lojistas não aderem ao Dia Livre de Impostos, com desconto de até 70%;
- Seca: licitação de R$ 720 mil para contratação de carro-pipa.

## Correções aplicadas

Arquivo alterado:

```text
backend/app/services/content_classifier.py
```

Principais ajustes:

1. `R$`, `desconto`, `promoção`, `oferta` e termos monetários deixam de ser sinal publicitário forte quando aparecem em contexto editorial.
2. Criado bloqueio para `noticia_com_valor_monetario_sem_cta`.
3. Notícias de economia/licitação/preço/imposto permanecem como:
   - `content_type = news`
   - `checking_status = rejeitado`
   - `market_status = ignorado`
   - `news_status = candidato`
4. Anúncios reais de infoproduto/curso continuam como publicidade quando houver:
   - domínio comercial externo (`app.oead.com.br`, Hotmart, Monetizze, Eduzz etc.);
   - CTA forte;
   - URL de banner;
   - evidência preservada.
5. `classification_reason` agora é limpo antes de nova reclassificação, evitando repetição de motivos em execuções sucessivas.
6. `classification_reason` deixou de contaminar o texto principal usado no cálculo de score.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois:

```bash
docker compose exec backend python -m app.scripts.reclassify_banner_items
```

Teste recomendado:

```bash
curl -X POST "http://localhost:8000/banners/scan/9b972aa2-f8a4-483b-a7d1-e979d86482fb?url=https://www.clickpb.com.br&save_rejected=true"
```

## Resultado esperado

O resultado geral deve permanecer próximo do teste anterior:

```json
{
  "detected": 29,
  "accepted": 5,
  "auditables": 5,
  "checking": {
    "auditavel": 5,
    "parcial": 0,
    "revisao": 0,
    "rejeitado": 24
  },
  "market_intelligence": {
    "included": 5
  },
  "news_monitoring": {
    "candidates": 24
  }
}
```

Os números podem variar conforme o portal carregue anúncios diferentes, mas a regra central é:

- notícia com valor monetário não deve virar publicidade;
- publicidade real com domínio/CTA/evidência segue auditável;
- tudo continua salvo quando `save_rejected=true`.
