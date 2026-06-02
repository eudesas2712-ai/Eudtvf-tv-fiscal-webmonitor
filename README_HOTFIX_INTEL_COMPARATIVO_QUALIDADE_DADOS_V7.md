# Hotfix V7 — Intel Comparativo com qualidade de dados

Este hotfix ajusta a leitura executiva do Intel Comparativo para evitar interpretação indevida de registros referenciais como prova de checking.

## Problema identificado

Na visão por segmento, registros de inteligência de mercado sem evidência auditável podiam aparecer como liderança competitiva, por exemplo: um anunciante com 29 evidências de mercado e 0 auditáveis.

Isso não é erro de coleta, mas precisa ser exibido como dado referencial, não como prova auditável.

## Correções aplicadas

### Backend

Arquivo alterado:

```text
backend/app/routers/intel_compare.py
```

Novos parâmetros em `GET /intel/compare/{project_id}`:

```text
evidence_scope=market      # visão ampla de mercado
evidence_scope=preserved   # somente itens com evidência preservada
evidence_scope=advertising # somente publicidade classificada
evidence_scope=auditavel   # somente checking auditável
include_zero_pairs=false   # evita matriz com pares zerados
```

Também aplicados aos relatórios:

```text
GET /intel/compare/report/pdf/{project_id}
GET /intel/compare/report/pptx/{project_id}
```

### Frontend

Arquivo alterado:

```text
frontend/src/app/intel/comparativo/page.tsx
```

Adicionado filtro visual:

```text
Modo de análise:
- Mercado amplo
- Somente com evidência preservada
- Somente publicidade classificada
- Somente checking auditável
```

Adicionado alerta executivo quando há evidências de mercado, mas 0 auditáveis.

## Resultado esperado

- O modo Mercado amplo continua servindo para inteligência de mercado referencial.
- O modo Checking auditável mostra apenas evidências comprovadas para auditoria.
- A matriz de confronto direto deixa de exibir confrontos entre anunciantes zerados como “equilibrados”.
- PDF/PPTX comparativos passam a respeitar o modo de análise selecionado.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/intel/comparativo
```

Teste recomendado:

1. Selecione o segmento Saúde.
2. Compare em modo Mercado amplo.
3. Altere para Somente checking auditável.
4. Gere PDF/PPTX nos dois modos para validar a diferença de leitura.
