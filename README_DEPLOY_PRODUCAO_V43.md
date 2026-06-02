# V43 — Preparação para publicação em servidor real

Este pacote prepara a TV Fiscal WebMonitor para publicação em VPS/servidor real com Docker, Nginx, volumes persistentes, variáveis de produção, backup e healthcheck.

## Objetivo

Levar a plataforma do ambiente local para uma instalação de produção com:

- backend FastAPI;
- frontend Next.js;
- PostgreSQL;
- Redis;
- MinIO;
- Nginx como reverse proxy;
- HTTPS via Certbot/Let’s Encrypt;
- volumes persistentes;
- backup automatizado;
- healthchecks para UptimeRobot.

## Domínio sugerido

```text
painelon.tvfiscal-pb.com.br
```

## Arquivos incluídos

```text
docker-compose.prod.yml
.env.production.example
nginx/tvfiscal-webmonitor.conf
scripts/deploy_prod.sh
scripts/check_prod.sh
scripts/backup_prod.sh
scripts/restore_postgres_prod.sh
docs/CHECKPOINT_TECNICO_GERAL_WEBMONITOR_V42_3.md
```

## Passo 1 — Preparar servidor

Servidor recomendado:

```text
Ubuntu 22.04 LTS ou 24.04 LTS
2 vCPU ou mais
4 GB RAM ou mais
80 GB SSD ou mais
Docker + Docker Compose Plugin
Nginx
Certbot
```

Instalação base:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y ca-certificates curl gnupg nginx certbot python3-certbot-nginx unzip zip
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
```

Faça logout/login no SSH após adicionar o usuário ao grupo docker.

## Passo 2 — Copiar projeto

No servidor:

```bash
mkdir -p /opt/tvfiscal-webmonitor
cd /opt/tvfiscal-webmonitor
```

Copie o projeto para essa pasta, incluindo este pacote V43.

## Passo 3 — Configurar ambiente

```bash
cp .env.production.example .env
nano .env
```

Ajuste senhas, domínio, tokens, SMTP e demais segredos.

## Passo 4 — Subir containers

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

Validar:

```bash
docker compose -f docker-compose.prod.yml ps
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

## Passo 5 — Configurar Nginx

```bash
sudo cp nginx/tvfiscal-webmonitor.conf /etc/nginx/sites-available/tvfiscal-webmonitor.conf
sudo ln -s /etc/nginx/sites-available/tvfiscal-webmonitor.conf /etc/nginx/sites-enabled/tvfiscal-webmonitor.conf
sudo nginx -t
sudo systemctl reload nginx
```

## Passo 6 — Ativar HTTPS

Após apontar o DNS do domínio para o IP da VPS:

```bash
sudo certbot --nginx -d painelon.tvfiscal-pb.com.br
```

## Passo 7 — Healthcheck externo

Configure no UptimeRobot:

```text
https://painelon.tvfiscal-pb.com.br/api/health/live
https://painelon.tvfiscal-pb.com.br/api/health/ready
```

Ou diretamente, se expuser backend internamente com segurança:

```text
https://painelon.tvfiscal-pb.com.br/health/live
https://painelon.tvfiscal-pb.com.br/health/ready
```

## Segurança inicial

- Trocar `ADMIN_TOKEN`.
- Trocar senha do usuário padrão `admin@tvfiscal.local`.
- Criar usuário administrativo real.
- Desativar ou resetar usuário padrão.
- Manter `AUTH_ENFORCEMENT_MODE=compat` durante homologação inicial.
- Migrar para `AUTH_ENFORCEMENT_MODE=strict` após validar todos os perfis.
- Não versionar `.env` real.

## Backup

Executar backup manual:

```bash
bash scripts/backup_prod.sh
```

Os backups ficam em:

```text
./data/backups
```

## Restauração PostgreSQL

```bash
bash scripts/restore_postgres_prod.sh ./data/backups/NOME_DO_BACKUP/postgres_webmonitor.dump
```

Use com cautela em produção.
