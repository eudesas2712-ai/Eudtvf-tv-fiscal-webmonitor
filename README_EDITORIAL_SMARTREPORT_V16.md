# TV Fiscal WebMonitor — Editorial SmartReport V16

Esta versão adiciona dois modelos de relatório editorial inspirados nos padrões enviados como referência:

1. **Sintético Executivo**
   - PDF em formato executivo, com dashboard visual.
   - KPIs: itens, fontes, vídeos/reels e risco.
   - Gráficos: sentimento, temas, ranking de fontes e linha do tempo.
   - Análise executiva automática.
   - Tabela de ocorrências resumidas.

2. **Analítico Expandido**
   - PDF com clipping detalhado.
   - Dashboard inicial.
   - Tabela analítica com data, veículo, tipo, tempo, tema, tom/risco, resumo e transcrição possível.
   - Página de amostras de evidência para print/portal, vídeo/reels e áudio/entrevista.
   - Nota metodológica sobre transcrição literal x transcrição possível.

## Novas rotas

```text
GET /editorial/report-synthetic-pdf/{project_id}
GET /editorial/report-sintetico-pdf/{project_id}
GET /editorial/report-analytical-pdf/{project_id}
GET /editorial/report-analitico-pdf/{project_id}
```

As rotas aceitam os mesmos filtros da tela editorial:

```text
q
source_name
term
sentiment
topic
date_from
date_to
```

## Tela

Em `/editorial`, foram adicionados três botões:

```text
PDF editorial simples
Sintético executivo
Analítico expandido
```

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Testes

```bash
curl -I "http://localhost:8000/editorial/report-sintetico-pdf/9b972aa2-f8a4-483b-a7d1-e979d86482fb"
curl -I "http://localhost:8000/editorial/report-analitico-pdf/9b972aa2-f8a4-483b-a7d1-e979d86482fb"
```

Depois acesse:

```text
http://localhost:3000/editorial
```

## Observação metodológica

O campo **transcrição possível** não deve ser tratado como transcrição literal de áudio/vídeo, exceto quando o sistema tiver arquivo MP3/MP4 e mecanismo de transcrição sincronizada. Na versão atual, ele é uma síntese textual derivada do conteúdo capturado, título, resumo, descrição pública e contexto da fonte.
