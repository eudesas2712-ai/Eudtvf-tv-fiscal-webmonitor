# Checkpoint técnico - Editorial + Social V3

Data: 04/07/2026

## Etapa concluída

Integração e validação do módulo Editorial, Social Monitor e Editorial + Social V3.

## Itens concluídos

- Tela Editorial funcionando.
- Tela Social Monitor funcionando.
- Tela Gestão de Fontes Sociais funcionando.
- Filtros aplicados no Editorial:
  - busca geral
  - fonte
  - termo
  - sentimento
  - tema
  - data inicial
  - data final
- KPIs da tela Editorial passaram a respeitar o recorte atual.
- Linha visual "Recorte atual" adicionada na tela Editorial.
- PDFs Editorial V3 passaram a usar summary filtrado.
- PDFs Editorial + Social V3 passaram a usar summary calculado a partir das linhas filtradas.
- Botão "Gerar pacote V3" passou a baixar 4 relatórios:
  - Sintético Executivo Premium V3
  - Analítico Executivo Expandido Premium V3
  - Sintético Editorial + Social V3
  - Analítico Editorial + Social V3

## Validação final

- /editorial: HTTP 200
- /social: HTTP 200
- /social-sources: HTTP 200

## Backup final da etapa

data/backups/pos_editorial_pacote_v3_4_relatorios_ok_20260704_161603.tar.gz

## Status

Estável.
