# TV Fiscal WebMonitor - Checklist de Deploy em Producao

## 1. Pre-requisitos da VPS

- Ubuntu Server atualizado.
- Docker instalado.
- Docker Compose instalado.
- Nginx instalado.
- Dominio apontando para o IP da VPS:
  - painelon.tvfiscal-pb.com.br
- Portas liberadas no firewall:
  - 80/tcp
  - 443/tcp
  - SSH apenas para IPs autorizados, quando possivel.

## 2. Arquivos principais

Arquivos usados em producao:

- docker-compose.prod.yml
- .env.production
- deploy/nginx/painelon.tvfiscal-pb.com.br.conf
- scripts/backup_prod.sh
- scripts/smoke_test_pos_restore.sh
- scripts/smoke_test_strict_auth.sh

## 3. Variaveis obrigatorias

Esta etapa NAO deve ser executada agora no ambiente local.

Quando estivermos na VPS, executar:

cp .env.production.example .env.production

Depois editar:

nano .env.production

Trocar obrigatoriamente:

- ADMIN_TOKEN
- SECRET_KEY
- DEFAULT_ADMIN_PASSWORD
- POSTGRES_PASSWORD
- DATABASE_URL
- MINIO_ROOT_PASSWORD
- MINIO_SECRET_KEY
- CORS_ORIGINS

Configuracao recomendada em producao:

AUTH_ENFORCEMENT_MODE=strict
ALLOW_ADMIN_TOKEN_QUERY=false
CORS_ORIGINS=https://painelon.tvfiscal-pb.com.br
NEXT_PUBLIC_ADMIN_TOKEN=

Observacao:
NEXT_PUBLIC_ADMIN_TOKEN deve ficar vazio em producao para nao expor token administrativo no navegador.

## 4. Subida dos containers na VPS

docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build

Verificar containers:

docker compose --env-file .env.production -f docker-compose.prod.yml ps

## 5. Nginx

Copiar configuracao:

sudo cp deploy/nginx/painelon.tvfiscal-pb.com.br.conf /etc/nginx/sites-available/painelon.tvfiscal-pb.com.br.conf
sudo ln -s /etc/nginx/sites-available/painelon.tvfiscal-pb.com.br.conf /etc/nginx/sites-enabled/painelon.tvfiscal-pb.com.br.conf
sudo nginx -t
sudo systemctl reload nginx

## 6. HTTPS com Certbot

sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d painelon.tvfiscal-pb.com.br

Testar renovacao:

sudo certbot renew --dry-run

## 7. Testes pos-deploy

Healthcheck:

curl -i https://painelon.tvfiscal-pb.com.br/health

Painel:

https://painelon.tvfiscal-pb.com.br

Smoke strict:

BASE_URL=https://painelon.tvfiscal-pb.com.br ADMIN_TOKEN=<TOKEN_REAL> ./scripts/smoke_test_strict_auth.sh

## 8. Backup

Executar backup manual:

bash scripts/backup_prod.sh

Agendar cron:

crontab -e

Exemplo diario as 02h30:

30 2 * * * cd /opt/tvfiscal-webmonitor && bash scripts/backup_prod.sh >> /var/log/tvfiscal-backup.log 2>&1

## 9. Seguranca operacional

- Nao versionar .env.production.
- Nao expor Postgres, Redis, OpenSearch ou MinIO publicamente.
- Manter backend e frontend atras do Nginx.
- Usar AUTH_ENFORCEMENT_MODE=strict em producao.
- Usar ALLOW_ADMIN_TOKEN_QUERY=false em producao.
- Trocar senha inicial apos criar usuarios reais.
- Revisar logs de autenticacao periodicamente.
- Testar restore de backup periodicamente.

## 10. Rollback

Tags uteis:

- v-pos-restore-validado-20260603
- v-main-auth-hardening-20260604
- v-main-backend-auth-hardening-20260604

Para rollback:

git checkout <TAG>
docker compose --env-file .env.production -f docker-compose.prod.yml up -d --build
