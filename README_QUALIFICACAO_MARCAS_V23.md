# TV Fiscal WebMonitor — V23
## Fila de Qualificação de Marcas / Pendentes de Identificação

Esta versão adiciona uma etapa operacional para resolver o volume de **Pendente de identificação** no Intel de Mercado.

## Objetivo

Evitar que itens sem anunciante reconhecido sejam tratados como líder de mercado. A plataforma passa a oferecer uma fila administrativa para:

- revisar grupos de peças pendentes;
- atribuir a um anunciante cadastrado;
- criar alias de reconhecimento para futuras coletas;
- remover ruídos da inteligência de mercado;
- reduzir progressivamente a participação de “Pendente de identificação”.

## Nova tela

```text
/admin/identificacao
```

## Novas rotas backend

```text
GET  /identification/pending/{project_id}
POST /identification/qualify/{project_id}
POST /identification/ignore/{project_id}
```

## Novas colunas em banner_items

```text
identification_status
identification_note
qualified_advertiser_id
qualified_at
```

As colunas são criadas automaticamente no bootstrap do backend.

## Como usar

1. Aplicar o pacote.
2. Subir backend e frontend.
3. Acessar `/admin/identificacao`.
4. Informar token administrativo.
5. Revisar grupos pendentes.
6. Escolher anunciante cadastrado.
7. Marcar se deseja criar alias.
8. Aplicar a qualificação.
9. Reabrir `/intel` e gerar relatórios novamente.

## Comando de aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Efeito esperado

- “Pendente de identificação” deixa de dominar o ranking quando for qualificado.
- O ranking passa a refletir anunciantes reais.
- Os relatórios ficam mais confiáveis comercialmente.
- Itens ignorados podem ser removidos do mercado sem apagar evidências preservadas.
