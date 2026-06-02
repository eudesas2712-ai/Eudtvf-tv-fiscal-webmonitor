# CHECKPOINT TÉCNICO — TV Fiscal WebMonitor

**Data de referência:** 28/05/2026  
**Fase consolidada:** Fechamento operacional do módulo publicitário/checking + início do módulo editorial/notícias  
**Status:** Publicitário/checking homologado em ambiente local Docker; módulo editorial iniciado com base operacional.

---

## 1. Estado atual consolidado

O TV Fiscal WebMonitor encontra-se com o módulo publicitário/checking em estado operacional avançado, incluindo:

- Painel executivo principal funcional;
- Painel Intel funcional;
- Intel Comparativo funcional;
- Tela de evidências operacionais funcional;
- Gestão de projetos monitorados funcional;
- Cadastros operacionais funcionais;
- Scheduler administrativo funcional;
- Scheduler com varredura por portais cadastrados;
- Portais padrão vinculáveis por projeto;
- Relatórios completos por projeto em PDF/PPTX;
- Relatórios comparativos Intel em PDF/PPTX;
- Modos de análise separados para mercado e checking;
- Classificação multicamadas validada.

Projeto ativo usado nos testes:

```text
9b972aa2-f8a4-483b-a7d1-e979d86482fb
```

---

## 2. Telas validadas

```text
/                         Painel executivo
/projects                 Projetos monitorados
/admin/cadastros          Cadastros operacionais
/admin/scheduler          Administração do Scheduler
/evidencias               Evidências operacionais
/intel                    Inteligência de Mercado
/intel/comparativo        Intel Comparativo
```

Nova tela iniciada nesta entrega:

```text
/editorial                Monitoramento editorial/notícias
```

---

## 3. Classificação multicamadas validada

A camada de classificação separa os itens capturados em usos distintos:

```text
checking_status:
- auditavel
- parcial
- revisao
- rejeitado

content_type:
- advertising
- news
- mixed
- unknown

market_status:
- incluido
- ignorado

news_status:
- candidato
- ignorado
```

Regras consolidadas:

- Publicidade auditável exige evidência preservada e score publicitário forte;
- Conteúdo editorial/notícia não entra como checking;
- Itens rejeitados para checking podem continuar úteis como notícia candidata;
- Inteligência de mercado não se confunde com prova documental;
- `accepted` e `auditables` passaram a contar somente itens realmente auditáveis;
- Matérias com valor monetário sem CTA comercial são notícia/editorial, não anúncio.

---

## 4. Intel Comparativo consolidado

O Intel Comparativo possui:

- Comparativo por segmento;
- Comparativo por anunciante;
- Múltiplos anunciantes selecionados;
- Período de análise;
- Ranking por evidências, investimento, portais e força;
- Matriz de confronto direto;
- Sobreposição de portais;
- Exportação PDF/PPTX.

Modos de análise:

```text
market_wide                 Mercado amplo
preserved_evidence          Somente com evidência preservada
classified_ads              Somente publicidade classificada
checking_auditable          Somente checking auditável
```

Ajuste executivo validado:

```text
presença unilateral
```

é usado quando apenas um anunciante possui dados no confronto. O termo:

```text
domínio competitivo
```

fica reservado para disputa real com dados nos dois lados.

---

## 5. Relatório Completo por Projeto consolidado

Rotas:

```text
GET /reports/project/summary/{project_id}?analysis_mode=market_wide
GET /reports/project/pdf/{project_id}?analysis_mode=checking_auditable
GET /reports/project/pptx/{project_id}?analysis_mode=classified_ads
```

O relatório consolida:

- Nome do projeto;
- Cliente;
- Segmento;
- Portais vinculados;
- Anunciantes e papéis;
- Evidências auditáveis;
- Inteligência de mercado;
- Candidatos a notícia;
- Ranking por anunciante;
- Ranking por portal;
- Leitura executiva automática;
- Avisos de leitura referencial quando não houver evidência auditável.

---

## 6. Gestão operacional consolidada

Telas e fluxos:

```text
/projects
```

Permite:

- Listar projetos;
- Criar projeto;
- Editar nome, cliente, segmento e descrição;
- Ativar/desativar projeto;
- Definir escopo de monitoramento;
- Vincular portais;
- Vincular anunciantes;
- Abrir Intel, Evidências e Comparativo no contexto do projeto;
- Gerar Relatório Completo PDF/PPTX.

```text
/admin/cadastros
```

Permite:

- Segmentos;
- Anunciantes/clientes;
- Aliases;
- Portais;
- Projeto ↔ Anunciante;
- Projeto ↔ Portal;
- Criação/vinculação de padrões comerciais.

```text
/admin/scheduler
```

Permite:

- Ver status;
- Executar snapshot manual;
- Executar varredura de portais cadastrados;
- Criar/vincular portais padrão;
- Ver histórico;
- Exportar CSV;
- Ativar/desativar scheduler.

---

## 7. Rotas principais do módulo publicitário/checking

```text
GET    /banners/{project_id}
POST   /banners/scan/{project_id}
GET    /intel/summary/{project_id}
GET    /intel/timeline/{project_id}
GET    /intel/report/pptx/{project_id}
GET    /intel/compare/{project_id}
GET    /intel/compare/report/pdf/{project_id}
GET    /intel/compare/report/pptx/{project_id}
GET    /reports/project/summary/{project_id}
GET    /reports/project/pdf/{project_id}
GET    /reports/project/pptx/{project_id}
```

---

## 8. Rotas principais de cadastros e scheduler

```text
GET/POST /registry/segments
GET/POST /registry/advertisers
GET/POST /registry/portals
POST     /registry/projects/{project_id}/advertisers
POST     /registry/projects/{project_id}/portals
POST     /registry/projects/{project_id}/bootstrap-portals
GET      /admin/scheduler/status
POST     /admin/scheduler/run-now
POST     /admin/scheduler/run-portal-scan-now
GET      /admin/scheduler/history
GET      /admin/scheduler/history/export.csv
```

---

## 9. Novo módulo editorial/notícias iniciado

Nesta entrega foi iniciado o módulo editorial com:

```text
/editorial
```

Recursos iniciais:

- Coleta editorial por projeto;
- Uso dos portais/fontes vinculados ao projeto;
- Detecção de termos monitorados;
- Detecção de aliases/anunciantes vinculados;
- Listagem de matérias;
- Filtros por busca, fonte, termo, sentimento, tema e período;
- Tema editorial básico;
- Sentimento básico;
- Score editorial;
- Detalhe da matéria;
- PDF editorial inicial.

Novas rotas:

```text
GET    /editorial/summary/{project_id}
GET    /editorial/items/{project_id}
POST   /editorial/run/{project_id}
GET    /editorial/report/{project_id}
GET    /editorial/report-pdf/{project_id}
DELETE /editorial/clear/{project_id}
```

Novos arquivos:

```text
backend/app/services/editorial_service.py
backend/app/routers/editorial.py
frontend/src/app/editorial/page.tsx
frontend/src/components/EditorialConsole.tsx
```

Campos incrementais adicionados à tabela `items`:

```text
source_name
summary
sentiment
sentiment_score
topic
editorial_score
published_at
```

---

## 10. Comandos de manutenção

Rebuild completo:

```bash
docker compose up -d --build --force-recreate backend frontend
```

Rebuild apenas frontend:

```bash
docker compose up -d --build --force-recreate frontend
```

Rebuild apenas backend:

```bash
python3 -m py_compile backend/app/services/editorial_service.py
python3 -m py_compile backend/app/routers/editorial.py
docker compose up -d --build --force-recreate backend
```

Teste de saúde:

```bash
curl http://localhost:8000/health
```

Executar coleta editorial:

```bash
curl -X POST \
  -H "X-Admin-Token: tvfiscal-admin-2026" \
  "http://localhost:8000/editorial/run/9b972aa2-f8a4-483b-a7d1-e979d86482fb?collect_all=true&limit_per_source=25"
```

Listar matérias editoriais:

```bash
curl "http://localhost:8000/editorial/items/9b972aa2-f8a4-483b-a7d1-e979d86482fb"
```

Gerar PDF editorial:

```text
http://localhost:8000/editorial/report-pdf/9b972aa2-f8a4-483b-a7d1-e979d86482fb
```

---

## 11. Próximos passos recomendados

1. Testar `/editorial` no navegador;
2. Rodar coleta editorial com portais vinculados;
3. Validar matérias coletadas;
4. Ajustar filtros, sentimento e temas;
5. Criar dashboard editorial executivo;
6. Criar relatório editorial PPTX;
7. Integrar editorial + publicitário no relatório unificado do projeto;
8. Criar alertas editoriais por termo, cliente, concorrente e sentimento;
9. Iniciar QA final do módulo publicitário/editorial integrado.

---

## 12. Status final deste checkpoint

```text
Módulo publicitário/checking: operacional e homologado
Evidências operacionais: operacional
Intel: operacional
Intel Comparativo: operacional
Relatórios por projeto: operacional
Gestão de projetos: operacional
Scheduler por portais cadastrados: operacional
Módulo editorial/notícias: iniciado — primeira versão operacional entregue
```
