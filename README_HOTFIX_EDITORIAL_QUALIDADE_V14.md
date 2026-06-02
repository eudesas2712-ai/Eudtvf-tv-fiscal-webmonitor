# Hotfix V14 — Qualidade do Monitoramento Editorial

Este hotfix melhora a qualidade do módulo editorial/notícias após a primeira coleta real.

## Problemas corrigidos

1. Falso positivo de marca/termo por substring.
   - Exemplo: `Amil` não deve ser detectado dentro de `família`.
   - A detecção agora usa fronteira lexical de palavra/frase completa.

2. Páginas de categoria/listagem entrando como matéria.
   - Exemplos filtrados: `Tudo sobre...`, `Últimas Notícias`, `Política - Análises`, `Esporte - Notícias`, `Mídias e Entretenimento`.

3. Limpeza de boilerplate.
   - Remove trechos como `All Right Reserved. Designed and Developed by WSCOM` e chamadas repetitivas de WhatsApp quando possível.

4. Reprocessamento de qualidade.
   - Nova rota para recalcular termos, tema, sentimento e score editorial dos itens já coletados.

## Novas rotas

```text
POST /editorial/reclassify/{project_id}?delete_listing_pages=true
```

Exemplo:

```bash
curl -X POST \
  -H "X-Admin-Token: tvfiscal-admin-2026" \
  "http://localhost:8000/editorial/reclassify/9b972aa2-f8a4-483b-a7d1-e979d86482fb?delete_listing_pages=true"
```

## Frontend

Na tela:

```text
/editorial
```

Foi adicionado o botão:

```text
Reprocessar qualidade
```

Esse botão aplica a nova regra aos itens já coletados.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois:

```bash
curl -X POST \
  -H "X-Admin-Token: tvfiscal-admin-2026" \
  "http://localhost:8000/editorial/reclassify/9b972aa2-f8a4-483b-a7d1-e979d86482fb?delete_listing_pages=true"
```

Ou use o botão na tela `/editorial`.

## Resultado esperado

- Menos falsos positivos em `Termos detectados`.
- Menos páginas de seção/listagem tratadas como matéria.
- Resumos mais limpos.
- Clipping editorial mais confiável para o próximo bloco de relatórios.
