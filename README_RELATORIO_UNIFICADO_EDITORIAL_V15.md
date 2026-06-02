# TV Fiscal WebMonitor — Relatório Unificado com Editorial V15

## Objetivo

Integra o módulo editorial/notícias ao Relatório Completo por Projeto, consolidando em um único PDF/PPTX:

- Publicidade/checking;
- Inteligência de mercado;
- Evidências auditáveis;
- Candidatos a notícia vindos da captura visual;
- Clipping editorial coletado em `/editorial`;
- Termos e marcas detectados nas matérias;
- Sentimento editorial;
- Temas recorrentes;
- Fontes editoriais.

## Rotas mantidas

```text
GET /reports/project/summary/{project_id}?analysis_mode=market_wide
GET /reports/project/pdf/{project_id}?analysis_mode=market_wide
GET /reports/project/pptx/{project_id}?analysis_mode=market_wide
```

Também funcionam os modos:

```text
market_wide
preserved_evidence
classified_ads
checking_auditable
```

## Novos dados no summary

O endpoint `/reports/project/summary/{project_id}` passa a retornar a chave:

```json
{
  "editorial": {
    "total_items": 0,
    "matched_items": 0,
    "sources_count": 0,
    "topics_count": 0,
    "sentiment_counts": {},
    "avg_editorial_score": 0,
    "top_sources": [],
    "top_topics": [],
    "top_terms": [],
    "latest_items": []
  }
}
```

## PDF/PPTX

O PDF e o PPTX do Relatório Completo agora incluem seções editoriais:

- Resumo editorial / clipping;
- Temas e termos editoriais;
- Últimas matérias monitoradas;
- Contagem de matérias e matérias com termos/marcas;
- Sentimento e score editorial.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Validação recomendada

```bash
curl "http://localhost:8000/reports/project/summary/9b972aa2-f8a4-483b-a7d1-e979d86482fb?analysis_mode=market_wide"
```

Depois gerar pela interface `/projects` ou diretamente:

```text
http://localhost:8000/reports/project/pdf/9b972aa2-f8a4-483b-a7d1-e979d86482fb?analysis_mode=market_wide
http://localhost:8000/reports/project/pptx/9b972aa2-f8a4-483b-a7d1-e979d86482fb?analysis_mode=market_wide
```

## Observação

A seção editorial não transforma notícia em publicidade. Ela entra como clipping eletrônico/monitoramento editorial, separada da prova documental de checking.
