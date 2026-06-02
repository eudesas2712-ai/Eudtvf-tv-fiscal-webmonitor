# TV Fiscal WebMonitor — Hotfix Usuários Ações V41.1

Este hotfix deixa explícitas as ações administrativas de usuários na tela `/admin/users`.

## Alterações

- Botões de ação diretamente na tabela de usuários:
  - Editar
  - Senha
  - Desativar/Reativar
  - Excluir
- Painel de edição completo:
  - nome
  - e-mail
  - perfil
  - status ativo/inativo
  - projetos liberados
- Bloco destacado para redefinição de senha.
- Exclusão definitiva para cadastro criado errado.
- Desativação preserva histórico e continua recomendada para usuários reais.
- Auditoria registra edição, redefinição, desativação e exclusão definitiva.

## Rotas alteradas/adicionadas

- `PUT /auth/users/{user_id}` agora aceita alteração de e-mail.
- `DELETE /auth/users/{user_id}` mantém comportamento seguro de desativação.
- `DELETE /auth/users/{user_id}/purge` exclui definitivamente o cadastro.
- `POST /auth/users/{user_id}/reset-password` redefine senha.

## Aplicação

```bash
docker compose -f docker-compose.yml -f docker-compose.backup-volume.override.yml up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/admin/users
```
