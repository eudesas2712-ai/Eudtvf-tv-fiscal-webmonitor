# TV Fiscal WebMonitor — V38
## Backup, manutenção e rotina de produção

Esta versão adiciona uma área administrativa para rotinas de produção do TV Fiscal WebMonitor.

## Nova tela

```text
/admin/maintenance
```

## Novas rotas backend

```text
GET    /maintenance/status
POST   /maintenance/backup
GET    /maintenance/backups
GET    /maintenance/backups/{filename}
DELETE /maintenance/backups/{filename}
POST   /maintenance/cleanup
GET    /maintenance/security-export.csv
```

## Recursos implementados

- Status operacional de manutenção.
- Geração de pacote ZIP de backup.
- Backup do PostgreSQL com `pg_dump`.
- Inclusão opcional de evidências do MinIO no pacote.
- Manifesto JSON dentro do backup.
- Listagem de backups disponíveis.
- Download de backup pelo painel.
- Exclusão controlada de backups antigos.
- Limpeza segura de logs antigos com modo simulação.
- Exportação CSV de segurança operacional.
- Instalação de `postgresql-client`, `zip` e `unzip` no Dockerfile do backend.

## Variáveis opcionais

```env
BACKUP_DIR=/app/backups
BACKUP_RETENTION_DAYS=15
MAX_BACKUP_LIST=50
```

## Aplicação

```bash
docker compose up -d --build --force-recreate backend frontend
```

## Testes recomendados

1. Abrir `/admin/maintenance`.
2. Confirmar que `pg_dump` aparece como OK.
3. Gerar backup somente com PostgreSQL.
4. Baixar o arquivo ZIP gerado.
5. Abrir o ZIP e conferir `manifest.json` e `postgres/postgres_webmonitor.dump`.
6. Rodar limpeza em modo simulação.
7. Rodar exportação de segurança CSV.

## Restauração do PostgreSQL

Dentro de um ambiente com acesso ao banco:

```bash
pg_restore \
  -h localhost \
  -p 5432 \
  -U webmonitor \
  -d webmonitor \
  --clean \
  --if-exists \
  postgres_webmonitor.dump
```

> Antes de restaurar em produção, faça um backup atualizado da base atual.

## Observação sobre MinIO

A inclusão de evidências MinIO pode gerar arquivos grandes. Para rotinas diárias, recomenda-se backup do PostgreSQL. Para fechamento de auditoria/documentação, recomenda-se habilitar também as evidências MinIO.
