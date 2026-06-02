# TV Fiscal WebMonitor — V42 — Permissões finas por perfil, projeto e módulo

## Objetivo

Esta versão fecha a camada de segurança funcional da plataforma com controle real de acesso por:

- perfil de usuário;
- módulos liberados;
- projetos permitidos;
- rotas backend;
- compatibilidade com o `X-Admin-Token` legado.

## O que foi implementado

### 1. Enforcement no backend

Novo serviço:

```text
backend/app/services/permissions_service.py
```

Ele aplica regras por rota:

- Dashboard Executivo;
- Projetos/Cadastros;
- Editorial;
- Banners;
- Evidências/Checking;
- Inteligência de Mercado;
- Intel Comparativo;
- Alertas;
- Caixa de Alertas;
- SLA;
- Relatórios;
- Notificações;
- Scheduler;
- Saúde/Manutenção;
- Usuários.

### 2. Middleware global no FastAPI

Arquivo alterado:

```text
backend/app/main.py
```

O middleware valida automaticamente:

- Bearer Token do usuário logado;
- módulos permitidos;
- projeto permitido quando a rota contém `project_id`;
- perfil permitido para ações de alteração;
- `X-Admin-Token` legado para compatibilidade operacional.

### 3. Modos de enforcement

Por padrão, a V42 inicia em modo compatível:

```env
AUTH_ENFORCEMENT_MODE=compat
```

Nesse modo:

- usuários logados são fiscalizados pelo backend;
- `X-Admin-Token` continua funcionando;
- chamadas legadas sem token ainda não são bloqueadas totalmente, evitando quebra imediata de rotinas antigas.

Para produção com bloqueio total:

```env
AUTH_ENFORCEMENT_MODE=strict
```

Nesse modo:

- chamadas protegidas sem sessão/autorização recebem `401`;
- perfis sem módulo recebem `403`;
- usuários sem acesso ao projeto recebem `403`.

### 4. Interceptor de autenticação no frontend

Arquivo alterado:

```text
frontend/src/lib/auth.ts
frontend/src/components/AppShell.tsx
```

O frontend passa a anexar automaticamente:

```text
Authorization: Bearer <token>
```

nas chamadas para o backend.

### 5. Gestão de módulos no cadastro/edição de usuários

Arquivo alterado:

```text
frontend/src/app/admin/users/page.tsx
```

Agora o administrador pode ajustar:

- projetos liberados;
- módulos liberados;
- perfil;
- status;
- senha;
- edição/exclusão/desativação.

### 6. Novas rotas de auditoria/visibilidade de acesso

```text
GET /auth/permissions-matrix
GET /auth/my-access
```

## Perfis recomendados

### Administrador
Acesso total.

### Gestor/Diretoria
Dashboard, projetos, editorial, banners, evidências, Intel, comparativo, alertas, relatórios, notificações, SLA e saúde.

### Operador de Monitoramento
Coletas, editorial, banners, evidências, alertas, caixa de alertas e scheduler.

### Comercial/Atendimento
Dashboard, Intel, comparativo, relatórios, projetos e alertas.

### Cliente externo
Dashboard, editorial, Intel, relatórios e alertas apenas dos projetos liberados.

### Auditor/Fiscal
Dashboard, banners, evidências, checking, alertas e relatórios de prova.

## Como aplicar

```bash
docker compose -f docker-compose.yml -f docker-compose.backup-volume.override.yml up -d --build --force-recreate backend frontend
```

## Testes recomendados

1. Entrar como Administrador.
2. Acessar `/admin/users`.
3. Criar usuário Cliente externo.
4. Selecionar apenas um projeto.
5. Liberar apenas os módulos desejados.
6. Entrar com esse usuário.
7. Conferir menu reduzido.
8. Tentar abrir rota de projeto não liberado.
9. Tentar abrir módulo não liberado.
10. Depois de validar, ativar `AUTH_ENFORCEMENT_MODE=strict` em ambiente de produção.

## Observação operacional

A V42 mantém compatibilidade com o `X-Admin-Token` para não quebrar scripts, curl, scheduler e rotinas administrativas antigas. A troca para `strict` deve ser feita depois de validar o fluxo de login, usuários e menus no navegador.
