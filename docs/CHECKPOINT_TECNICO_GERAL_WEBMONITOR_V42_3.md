# CHECKPOINT TÉCNICO GERAL — TV Fiscal WebMonitor

**Versão consolidada:** V42.3  
**Data de referência:** 30/05/2026  
**Projeto principal de testes:** `9b972aa2-f8a4-483b-a7d1-e979d86482fb`  
**Estado geral:** plataforma operacional localmente, com módulos principais homologados e pronta para preparação de publicação em servidor real.

---

## 1. Objetivo da plataforma

A TV Fiscal WebMonitor é uma plataforma executiva de monitoramento editorial, clipping eletrônico, auditoria de publicidade digital, inteligência de mercado, evidências, alertas, notificações, SLA e relatórios premium.

O sistema consolida:

- monitoramento de notícias e menções;
- captura e classificação de banners/publicidade digital;
- checking publicitário com evidência preservada;
- inteligência de mercado por anunciante, portal, segmento e investimento estimado;
- qualificação manual/automática de marcas não identificadas;
- relatórios PDF/PPTX/CSV;
- alertas executivos;
- motor de notificações por e-mail, SMS, WhatsApp e webhook;
- caixa operacional de alertas;
- SLA e escalonamento;
- manutenção, backup e saúde operacional;
- login, usuários, perfis e permissões finas.

---

## 2. Estado consolidado por versão

### V11 a V15 — Editorial/notícias

- Módulo editorial iniciado e operacional.
- Rotas de coleta, listagem e relatório editorial.
- Reprocessamento de qualidade.
- Correção de falsos positivos, como `Amil` dentro de palavras maiores.
- Remoção/redução de páginas de categoria/listagem.
- Integração editorial ao relatório completo por projeto.

### V16 a V20 — Relatórios editoriais premium

- PDF Editorial Sintético Executivo.
- PDF Editorial Analítico Expandido.
- Dashboard com KPIs, sentimento, temas, fontes e linha do tempo.
- Página de evidências.
- Ajustes de cabeçalho e logo.
- Dashboard moderno V20 validado.

### V21 a V25 — Publicidade, Intel e qualificação de marcas

- Relatórios publicitários/checking em padrão premium.
- Correção para separar `Não identificado` de anunciantes reais.
- Fila de qualificação de marcas pendentes.
- Aprendizado por aliases.
- Autoidentificação pós-coleta/scheduler.
- Exportação CSV de pendentes e ações.

### V26 a V36 — Alertas, notificações, SLA e relatórios gerenciais

- Central de Alertas Executivos.
- Motor de Notificações.
- E-mail SMTP real homologado.
- Envio automático por regra via e-mail real homologado.
- Preparação para SMS/WhatsApp real com provedores externos.
- Integração de notificações ao Scheduler e coleta editorial.
- Caixa de Alertas Operacional.
- SLA e Escalonamento.
- Relatório Gerencial de Alertas e SLA em PDF/PPTX/CSV.

### V37 a V40.1 — Produção, manutenção e saúde operacional

- Dashboard Executivo Geral na home `/`.
- Backup PostgreSQL com ZIP e manifesto.
- Persistência de backup via volume externo `./data/backups:/app/backups`.
- Backup automático.
- Saúde do sistema com PostgreSQL, Redis, MinIO, Scheduler, disco, backup e notificações.
- Endpoints para UptimeRobot.
- Saneamento de erros de homologação/teste.

### V41 a V42.3 — Login, usuários e permissões finas

- Login em `/login`.
- Gestão de usuários em `/admin/users`.
- Perfis de acesso:
  - Administrador;
  - Gestor/Diretoria;
  - Operador de Monitoramento;
  - Comercial/Atendimento;
  - Cliente Externo;
  - Auditor/Fiscal.
- Criar, editar, redefinir senha, desativar, reativar e excluir usuários criados incorretamente.
- Auditoria de ações de usuário.
- Permissões reais por perfil, projeto e módulo.
- Middleware de autenticação e autorização.
- Compatibilidade com `X-Admin-Token` preservada.
- Correção de carregamento da Inteligência de Mercado após permissões finas.
- Otimização `/intel/summary` com consultas SQL agregadas.

---

## 3. Telas principais validadas

- `/` — Dashboard Executivo Geral.
- `/login` — Login.
- `/admin/users` — Usuários e perfis.
- `/projects` — Projetos monitorados.
- `/editorial` — Monitoramento editorial.
- `/banners` — Banners capturados.
- `/evidences` — Evidências operacionais.
- `/intel` — Inteligência de Mercado.
- `/intel/comparativo` — Intel Comparativo.
- `/admin/scheduler` — Scheduler.
- `/admin/registries` ou cadastros operacionais — Portais, anunciantes e segmentos.
- `/admin/identificacao` — Qualificação de marcas.
- `/alerts` — Central de Alertas.
- `/alerts/inbox` — Caixa de Alertas.
- `/alerts/sla` — SLA e Escalonamento.
- `/alerts/reports` — Relatório Gerencial de Alertas.
- `/admin/notifications` — Motor de Notificações.
- `/admin/maintenance` — Manutenção e Backup.
- `/admin/system-health` — Saúde do Sistema.
- `/docs` ou `/swagger` — API/Swagger.

---

## 4. Relatórios disponíveis

### Editorial

- Sintético Executivo PDF.
- Analítico Expandido PDF.
- Relatório editorial padrão.

### Publicidade/checking/inteligência

- Intel de Mercado PDF.
- Intel de Mercado PPTX.
- Intel Comparativo PDF.
- Intel Comparativo PPTX.
- Relatório Completo por Projeto PDF.
- Relatório Completo por Projeto PPTX.

### Alertas e SLA

- Relatório Gerencial de Alertas PDF.
- Relatório Gerencial de Alertas PPTX.
- Exportação CSV operacional.

### Produção/manutenção

- Backup ZIP com manifesto JSON.
- Exportação de segurança CSV.
- Relatório técnico de saúde PDF.

---

## 5. Canais de notificação

### Homologado

- E-mail real via SMTP.
- E-mail automático por regra.
- Painel interno.

### Preparado, pendente de provedor

- SMS: Webhook, Twilio, Zenvia, TotalVoice.
- WhatsApp: Webhook, Zenvia, Meta WhatsApp Cloud API.
- Webhook genérico.

Observação: SMS/WhatsApp exigem contratação/configuração de provedor externo ou webhook próprio.

---

## 6. Comandos principais de execução local

### Subir com volume persistente de backup

```bash
docker compose -f docker-compose.yml -f docker-compose.backup-volume.override.yml up -d --build --force-recreate backend frontend
```

### Conferir containers

```bash
docker compose ps
```

### Healthcheck

```bash
curl http://localhost:8000/health
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
curl http://localhost:8000/system/health/uptime
```

### Testar Intel otimizado

```bash
curl --max-time 20 -H "X-Admin-Token: tvfiscal-admin-2026" \
"http://localhost:8000/intel/summary/9b972aa2-f8a4-483b-a7d1-e979d86482fb"
```

---

## 7. Variáveis relevantes de produção

```env
APP_TIMEZONE=America/Sao_Paulo
TZ=America/Sao_Paulo

AUTH_ENFORCEMENT_MODE=compat
# Para produção após validação completa:
# AUTH_ENFORCEMENT_MODE=strict

BACKUP_DIR=/app/backups
AUTO_BACKUP_ENABLED=true
AUTO_BACKUP_INTERVAL_HOURS=24
AUTO_BACKUP_CHECK_EVERY_MINUTES=60
AUTO_BACKUP_INCLUDE_MINIO=false
BACKUP_WARNING_HOURS=24
BACKUP_ERROR_HOURS=168

NOTIFICATION_DRY_RUN=true
EMAIL_ALERTS_ENABLED=true
SMTP_HOST=
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=
```

---

## 8. Pendências reais

1. Publicação em servidor real/VPS.
2. Configuração de domínio e HTTPS.
3. Variáveis de produção e segredos.
4. Volumes persistentes oficiais para PostgreSQL, Redis, MinIO e backups.
5. Hardening básico do backend/frontend.
6. Configuração de UptimeRobot externo.
7. Contratação/configuração futura de SMS/WhatsApp, se desejado.
8. Migração gradual de `AUTH_ENFORCEMENT_MODE=compat` para `strict` após validação completa dos perfis.
9. Backup externo opcional para nuvem ou storage remoto.

---

## 9. Próxima etapa recomendada

**V43 — Preparação para publicação em servidor real**

Escopo recomendado:

- `docker-compose.prod.yml`;
- `.env.production.example`;
- Nginx reverse proxy;
- HTTPS com Certbot/Let’s Encrypt;
- volumes persistentes;
- scripts de deploy, backup e restauração;
- checklists de segurança;
- documentação para VPS;
- preparação para domínio `painelon.tvfiscal-pb.com.br`.

---

## 10. Observação final

A plataforma está em estágio avançado de homologação local. A próxima fase deve priorizar estabilidade, segurança, persistência e publicação controlada em ambiente real.
