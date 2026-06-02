# TV Fiscal WebMonitor — Editorial Premium Dashboard Moderno V20

## Objetivo
Refinar visualmente a primeira página dos relatórios editoriais premium, com padrão mais moderno de dashboard executivo e logomarca sem fundo branco no cabeçalho.

## Alterações principais

### 1. Cabeçalho premium atualizado
- Logo TV Fiscal sem caixa/fundo branco.
- Nova versão de logo para cabeçalho escuro: `backend/app/assets/logo_tvfiscal_header.png`.
- Cabeçalho com kicker editorial: `EDITORIAL INTELLIGENCE · TV FISCAL WEBMONITOR`.
- Mantida faixa azul escura institucional e linha vermelha TV Fiscal.

### 2. Dashboard inicial modernizado
- Donut moderno de sentimento com total no centro.
- Barras horizontais limpas sem eixo pesado.
- Timeline simplificada com rótulos diretos.
- Cards de KPI com acentos coloridos por bloco.
- Bloco de leitura executiva mais integrado ao layout.

### 3. Sintético Executivo
- Página 1 otimizada para permanecer em uma página.
- Redução de excesso de linhas na tabela resumida.
- Melhor hierarquia visual entre KPIs, gráficos e leitura executiva.

### 4. Analítico Expandido
- Primeira página com o mesmo padrão premium do sintético.
- Mantida estrutura de clipping analítico detalhado e amostras de evidência.

## Arquivos alterados
- `backend/app/services/editorial_report_generator.py`
- `backend/app/assets/logo_tvfiscal_header.png`
- `frontend/public/logo-tv-fiscal-clean_header.png`

## Aplicação
```bash
docker compose up -d --build --force-recreate backend frontend
```

## Teste
Acessar:

```text
http://localhost:3000/editorial
```

Gerar:
- Sintético executivo
- Analítico expandido

Validar:
- logo sem fundo branco;
- cabeçalho limpo;
- primeira página com dashboard mais moderno;
- sintético em uma página sempre que houver limite padrão de ocorrências.
