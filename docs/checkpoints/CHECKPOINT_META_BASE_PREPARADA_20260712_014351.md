# Checkpoint — Base Meta Instagram/Facebook

## Status

A base técnica dos conectores Meta foi preparada no Social Monitor.

## Entregas

- Serviço base `social_meta_collector.py` criado.
- Rotas backend adicionadas:
  - `/social/instagram/collect/{project_id}`
  - `/social/facebook/collect/{project_id}`
- Frontend liberado para acionar coleta manual de Instagram e Facebook.
- Páginas `/social` e `/social-sources` validadas com HTTP 200.
- Rotas Meta respondem de forma controlada quando o token não está configurado.

## Estado atual

Coleta real ainda depende de token Meta e permissões da Graph API.

## Próximo passo

Configurar token Meta e definir tipos de fonte aceitos: hashtag, perfil profissional, página, page_id ou URL identificável.
