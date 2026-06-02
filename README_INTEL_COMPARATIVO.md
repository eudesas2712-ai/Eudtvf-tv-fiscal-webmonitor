# TV Fiscal WebMonitor — Intel Comparativo

## Objetivo

Este bloco adiciona uma visão executiva de comparação competitiva por segmento e por anunciante cadastrado.

A tela foi criada para responder perguntas como:

- Unimed x Hapvida no segmento Saúde;
- Claro x Vivo x TIM em Telecom;
- Casas Bahia x Magalu em Varejo;
- Caixa x Banco do Brasil em Bancos;
- presença por portal, formatos, investimento estimado e evidências auditáveis.

## Nova rota frontend

```text
http://localhost:3000/intel/comparativo
```

A rota também foi adicionada ao menu lateral como **Intel Comparativo**.

## Nova rota backend

```text
GET /intel/compare/{project_id}
```

Parâmetros opcionais:

```text
segment_id=UUID do segmento
advertiser_ids=UUID1,UUID2,UUID3
date_from=YYYY-MM-DD
date_to=YYYY-MM-DD
max_advertisers=12
```

Exemplo:

```bash
curl "http://localhost:8000/intel/compare/9b972aa2-f8a4-483b-a7d1-e979d86482fb?segment_id=SEU_SEGMENT_ID"
```

## Métricas entregues

Para cada anunciante comparado:

- evidências de mercado;
- evidências auditáveis para checking;
- investimento estimado;
- share por investimento;
- share por volume;
- score médio de publicidade;
- score médio de mercado;
- score de visibilidade;
- portais utilizados;
- formatos capturados;
- últimas evidências preservadas;
- força competitiva.

## Matriz de confronto direto

A API também gera uma matriz par a par entre anunciantes:

```text
Unimed x Hapvida
Claro x Vivo
Casas Bahia x Magalu
```

Para cada par, calcula:

- líder;
- equilíbrio competitivo;
- classificação do embate;
- diferença de investimento;
- diferença de evidências.

## Sobreposição de portais

A tela também mostra em quais portais dois anunciantes competem simultaneamente.

Isso permite identificar disputa direta em veículos específicos.

## Como aplicar

```bash
docker compose up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/intel/comparativo
```

## Teste recomendado

1. Acesse `/admin/cadastros`.
2. Clique em **Criar padrões comerciais**, caso ainda não tenha criado.
3. Cadastre/vincule os anunciantes desejados ao projeto.
4. Acesse `/intel/comparativo`.
5. Selecione o segmento Saúde.
6. Selecione Unimed e Hapvida, se houver evidências cadastradas/aliases.
7. Verifique ranking, matriz de confronto e evidências.

## Observação

A comparação depende do casamento por aliases cadastrados. Para maior precisão, cadastre variações do nome da marca em `/admin/cadastros`, por exemplo:

```text
Unimed
Unimed JP
Unimed João Pessoa
Hapvida
Hapvida Saúde
NotreDame Intermédica
```
