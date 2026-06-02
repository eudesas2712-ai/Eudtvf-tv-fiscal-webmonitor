# TV Fiscal WebMonitor — Relatórios Intel e Comparativo

## Entrega desta versão

Esta versão integra a nova lógica de evidências e comparação competitiva aos relatórios executivos.

## Novidades

### 1. Painel Intel

O botão de relatório agora respeita os filtros aplicados no painel:

- `segment_id`
- `advertiser_id`

Foram adicionadas duas saídas:

- `GET /intel/report/pptx/{project_id}`
- `GET /intel/report/pdf/{project_id}`

Ambas aceitam os filtros acima por query string.

### 2. Relatório executivo com qualificação de evidências

O PDF/PPTX do Intel agora diferencia:

- itens detectados;
- itens usados em inteligência de mercado;
- publicidade auditável;
- itens em revisão/parcial;
- candidatos a notícia;
- evidências preservadas;
- rejeitados para checking.

Isso evita tratar notícia/editorial como anúncio confirmado.

### 3. Intel Comparativo

A tela `/intel/comparativo` ganhou exportação do recorte atual em:

- PDF comparativo;
- PPTX comparativo.

Novas rotas:

```text
GET /intel/compare/report/pdf/{project_id}
GET /intel/compare/report/pptx/{project_id}
```

Parâmetros aceitos:

```text
segment_id
advertiser_ids
date_from
date_to
max_advertisers
```

### 4. Conteúdo do relatório comparativo

O relatório comparativo inclui:

- KPIs do recorte;
- ranking por anunciante;
- evidências de mercado;
- auditáveis;
- investimento estimado;
- share de investimento;
- score de força competitiva;
- matriz de confronto direto;
- sobreposição de portais;
- insights automáticos.

## Como aplicar

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Testes recomendados

### Intel geral

```text
http://localhost:3000/intel
```

Aplicar filtros por segmento/anunciante e testar:

- Gerar PPTX Completo;
- Gerar PDF Executivo.

### Intel comparativo

```text
http://localhost:3000/intel/comparativo
```

Selecionar segmento e anunciantes, depois testar:

- Gerar PPTX Comparativo;
- Gerar PDF Comparativo.

## Observação técnica

A compilação Python do backend foi validada com `py_compile`. O build Next.js deve ser validado no container do projeto via Docker.
