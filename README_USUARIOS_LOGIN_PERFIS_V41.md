# TV Fiscal WebMonitor — V41
## Gestão de usuários, login e perfis de acesso

Esta versão adiciona autenticação por usuário, perfis de acesso, tela de login, gestão administrativa de usuários e auditoria de acesso.

## Novas telas

- `/login` — Tela de entrada segura da plataforma.
- `/admin/users` — Gestão de usuários, perfis, status, senha inicial/redefinição e auditoria.

## Perfis criados

- Administrador
- Gestor/Diretoria
- Operador de Monitoramento
- Comercial/Atendimento
- Cliente externo
- Auditor/Fiscal

## Backend

Novas rotas:

```text
POST /auth/login
GET  /auth/me
GET  /auth/roles
GET  /auth/users
POST /auth/users
PUT  /auth/users/{user_id}
POST /auth/users/{user_id}/reset-password
DELETE /auth/users/{user_id}
GET  /auth/projects-summary
GET  /auth/audit
POST /auth/bootstrap-admin
```

Novas tabelas:

```text
app_users
auth_audit_logs
```

## Primeiro acesso padrão

Por padrão, se não houver usuário, o sistema cria:

```text
E-mail: admin@tvfiscal.local
Senha: tvfiscal-admin-2026
Perfil: Administrador
```

Para alterar via `.env`:

```env
DEFAULT_ADMIN_EMAIL=eudesas2712@gmail.com
DEFAULT_ADMIN_PASSWORD=uma_senha_forte
DEFAULT_ADMIN_NAME=Administrador TV Fiscal
APP_AUTH_SECRET=chave_longa_para_assinar_sessoes
APP_AUTH_TOKEN_TTL_SECONDS=43200
```

## Aplicação

```bash
docker compose -f docker-compose.yml -f docker-compose.backup-volume.override.yml up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/login
```

## Observações de produção

- Altere a senha do admin padrão no primeiro uso.
- Configure `APP_AUTH_SECRET` com valor forte em produção.
- O token antigo `X-Admin-Token` continua compatível para rotas administrativas e automações internas.
- O bearer token do usuário administrador também passa a ser aceito nas rotas administrativas existentes.

## Resultado esperado

A plataforma passa a ter controle de acesso por usuário, perfil operacional, módulos visíveis por perfil e trilha de auditoria de login/ações administrativas.
