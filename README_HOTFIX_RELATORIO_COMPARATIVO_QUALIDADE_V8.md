# Hotfix V8 — Qualidade Executiva dos Relatórios Comparativos

## Objetivo

Corrigir a leitura executiva dos relatórios PDF/PPTX do Intel Comparativo para diferenciar com clareza:

- mercado amplo / leitura referencial;
- evidência preservada;
- publicidade classificada;
- checking auditável.

## Problema corrigido

Os relatórios comparativos podiam exibir evidências de mercado sem nenhuma peça auditável e ainda assim gerar leitura competitiva como se fosse checking comprovado.

Também podiam apresentar “par mais equilibrado” mesmo quando o equilíbrio era 0.0, ou seja, quando havia domínio de um anunciante e ausência de dados dos demais.

## Alterações

### Backend

Arquivos alterados:

- `backend/app/routers/intel_compare.py`
- `backend/app/services/compare_report_generator.py`

### Correções aplicadas

1. `quality_notice` agora é retornado pela API quando há evidências de mercado, mas 0 auditáveis.
2. Insights automáticos agora indicam o modo de análise usado.
3. Quando `auditables = 0`, a leitura deixa claro que é referencial, não checking comprovado.
4. Pares com equilíbrio 0.0 não são mais descritos como “par mais equilibrado”.
5. Se não há confronto equilibrado, o relatório informa domínio competitivo ou ausência de dados de um lado.
6. PDF e PPTX agora exibem o modo de análise.
7. PDF e PPTX exibem aviso de qualidade de dado quando aplicável.
8. A matriz de confronto mostra “Sem confronto competitivo válido” quando não há pares úteis.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Teste recomendado

1. Acesse `/intel/comparativo`.
2. Selecione segmento Saúde.
3. Gere PDF/PPTX em “Mercado amplo”.
4. Confirme que aparece aviso de leitura referencial quando houver 0 auditáveis.
5. Gere PDF/PPTX em “Somente checking auditável”.
6. Confirme que os relatórios não tratam mercado referencial como prova de checking.

