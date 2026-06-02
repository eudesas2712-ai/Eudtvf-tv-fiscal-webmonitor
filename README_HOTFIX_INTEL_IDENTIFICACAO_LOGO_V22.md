# TV Fiscal WebMonitor — Hotfix V22
## Intel de Mercado: identificação comercial + logo correta

Este hotfix corrige dois pontos observados após a aplicação dos relatórios premium V21:

1. **Alto volume de “Não identificado” no Intel de Mercado**
2. **Logo textual/inconsistente nos relatórios publicitários em relação aos relatórios editoriais V20**

## Ajustes implementados

### 1. “Não identificado” deixa de ser tratado como anunciante líder
O bloco passa a ser tratado como:

- **Pendente de identificação**
- fila de auditoria comercial
- inventário a qualificar por alias/OCR/revisão humana

O sistema continua preservando o volume e o investimento estimado, mas não usa esse bloco como líder de mercado, rival principal ou principal anunciante identificado.

### 2. Novo resumo de qualidade da identificação
Foram adicionados indicadores de qualidade:

- itens pendentes de identificação;
- share pendente;
- investimento estimado pendente;
- anunciantes efetivamente identificados;
- alertas de qualificação comercial.

### 3. Ranking separado
O Intel passa a mostrar:

- **Top anunciantes identificados**;
- pendentes de identificação em box próprio;
- portais e investimento preservados.

### 4. Competitive map mais seguro
Itens pendentes de identificação deixam de contaminar:

- mapa competitivo;
- rivalidade principal;
- papéis competitivos;
- insights de liderança.

### 5. Relatório Completo por Projeto
O relatório completo também passa a tratar pendentes de identificação como qualidade de base, não como anunciante líder.

### 6. Logo correta nos relatórios publicitários
O PDF do Intel de Mercado agora usa a imagem:

```text
backend/app/assets/logo_tvfiscal_header.png
```

A mesma lógica do editorial premium V20 foi aplicada ao Intel publicitário.

### 7. PPTX do Intel
Os slides do Intel também passam a usar a logo do arquivo acima no cabeçalho.

## Arquivos alterados

```text
backend/app/services/identification_quality.py
backend/app/routers/market_intelligence.py
backend/app/routers/project_reports.py
backend/app/services/report_generator.py
backend/app/services/ppt_generator.py
backend/app/services/project_report_generator.py
backend/app/templates/intel_report.html
frontend/src/app/intel/page.tsx
```

## Como aplicar

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Como testar

1. Abrir o Intel:

```text
http://localhost:3000/intel
```

2. Conferir se aparece:

```text
Anunciantes identificados
Pendentes ID
Top Anunciantes Identificados
Qualidade de identificação
```

3. Gerar o PDF:

```text
/intel → Gerar PDF Executivo
```

4. Gerar o PPTX:

```text
/intel → Gerar PPTX Completo
```

5. Conferir se:

- a logo aparece igual ao padrão editorial;
- “Pendente de identificação” não aparece como líder de mercado;
- o ranking de anunciantes mostra apenas identificados;
- o volume pendente aparece como alerta/qualidade de base.

## Observação operacional

Este hotfix não oculta os não identificados. Ele preserva os dados, mas muda a interpretação executiva. Para reduzir efetivamente o volume pendente, o próximo passo é alimentar aliases, melhorar OCR/visual matching e revisar evidências pendentes.
