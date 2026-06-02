# TV Fiscal WebMonitor - Editorial Premium Visual V17

Esta versão redesenha os relatórios editoriais Sintético Executivo e Analítico Expandido com identidade visual premium da TV Fiscal.

## Principais melhorias

- Cabeçalho executivo premium com faixa azul escura, destaque vermelho institucional e logo TV Fiscal.
- Cards de KPIs com acabamento de dashboard.
- Dashboard editorial com blocos visuais para sentimento, temas dominantes, ranking de fontes e linha do tempo.
- Sintético Executivo otimizado para uma página.
- Analítico Expandido com capa/dashboard, clipping em cards analíticos e página de evidências.
- Badges visuais de sentimento e risco.
- Página de amostras de evidência com cards para print/portal, vídeo/reels e áudio/entrevista.
- Rodapé institucional TV Fiscal preservado.

## Arquivo principal alterado

```text
backend/app/services/editorial_report_generator.py
```

## Rotas já existentes mantidas

```text
GET /editorial/report-sintetico-pdf/{project_id}
GET /editorial/report-analitico-pdf/{project_id}
```

## Como aplicar

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Como testar

Acesse:

```text
http://localhost:3000/editorial
```

E gere novamente:

```text
Sintético executivo
Analítico expandido
```

## Observação metodológica

A expressão "transcrição possível" continua significando síntese textual derivada do conteúdo capturado, título, resumo, descrição pública e contexto da fonte monitorada. Transcrição literal sincronizada depende da captura real de MP3/MP4 e será tratada em etapa posterior.
