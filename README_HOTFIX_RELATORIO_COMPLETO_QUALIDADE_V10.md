# Hotfix V10 — Relatório Completo por Projeto com Qualidade de Dados

Este hotfix aplica ao **Relatório Completo por Projeto** a mesma lógica de qualidade já validada no Intel Comparativo.

## Objetivo

Evitar que leitura de mercado referencial seja confundida com checking comprovado.

## Novidades

### Backend

Rotas de relatório por projeto agora aceitam:

```text
analysis_mode=market_wide
analysis_mode=preserved_evidence
analysis_mode=classified_ads
analysis_mode=checking_auditable
```

Rotas afetadas:

```text
GET /reports/project/summary/{project_id}
GET /reports/project/pdf/{project_id}
GET /reports/project/pptx/{project_id}
```

### Modos de análise

```text
market_wide
Mercado amplo. Usa itens com market_status = incluido.

preserved_evidence
Somente itens de mercado com evidência preservada.

classified_ads
Somente itens classificados como publicidade.

checking_auditable
Somente itens com checking_status = auditavel.
```

### PDF/PPTX

Agora exibem:

- Modo de análise aplicado;
- alerta de leitura referencial quando houver mercado sem auditáveis;
- alerta quando não houver evidência auditável no recorte;
- separação explícita entre itens analisados, auditáveis e candidatos a notícia.

### Frontend

Na tela `/projects`, foi adicionado um seletor de modo de relatório antes dos botões de PDF/PPTX.

Na tela `/intel`, o relatório completo passa a chamar `analysis_mode=market_wide` por padrão e inclui botão rápido para **PDF Checking Auditável**.

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Testes recomendados

```text
1. Abrir /projects.
2. Selecionar projeto.
3. Gerar relatório em modo Mercado amplo.
4. Gerar relatório em modo Checking auditável.
5. Confirmar que o PDF/PPTX avisam quando a leitura é apenas referencial.
6. Confirmar que o modo Checking auditável não mistura evidência de mercado com prova documental.
```
