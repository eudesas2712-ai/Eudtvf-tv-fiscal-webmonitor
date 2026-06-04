# TV Fiscal WebMonitor — Checklist de Endurecimento de Autenticação

Base segura:
- Tag: v-pos-restore-validado-20260603
- Branch de evolução: hardening/auth-admin-seguro

## Objetivo

Remover gradualmente a dependência de token administrativo fixo no frontend e consolidar autenticação por sessão/login, sem quebrar a versão restaurada e validada.

## Etapas

### 1. Auditoria de tokens
- [ ] Mapear todos os usos de X-Admin-Token.
- [ ] Mapear todos os usos de tvfiscal-admin-2026.
- [ ] Mapear authHeaders().
- [ ] Mapear interceptors de fetch.
- [ ] Separar rotas públicas, rotas administrativas e rotas de sistema.

### 2. Frontend
- [ ] Criar helper único para chamadas autenticadas.
- [ ] Remover token fixo de páginas client-side.
- [ ] Centralizar leitura de sessão.
- [ ] Tratar sessão expirada com redirecionamento controlado.
- [ ] Exibir mensagem amigável quando o usuário perder sessão.

### 3. Backend
- [ ] Revisar dependências de autenticação administrativa.
- [ ] Padronizar verificação JWT.
- [ ] Manter X-Admin-Token apenas para rotinas internas ou manutenção.
- [ ] Registrar auditoria das ações sensíveis.
- [ ] Bloquear ações administrativas para perfis sem permissão.

### 4. Segurança operacional
- [ ] Mover tokens sensíveis para .env.
- [ ] Garantir que nenhum segredo real vá para o GitHub.
- [ ] Criar .env.example sem senhas reais.
- [ ] Validar CORS para ambiente local e produção.
- [ ] Preparar configuração para VPS.

### 5. Validação
- [ ] Rodar smoke test.
- [ ] Validar login.
- [ ] Validar Projetos.
- [ ] Validar Cadastros.
- [ ] Validar Usuários e Perfis.
- [ ] Validar Scheduler.
- [ ] Validar Notificações.
- [ ] Validar Qualificação de marcas.

## Regra de segurança

Toda alteração deve preservar a tag de rollback:

v-pos-restore-validado-20260603
