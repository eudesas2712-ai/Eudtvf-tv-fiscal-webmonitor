# TV Fiscal WebMonitor — V40 Persistência de Backups e Saneamento Operacional

Esta versão fortalece a operação de produção após a V39 de saúde/uptime.

## Implementado

1. **Persistência de backups**
   - Inclusão do arquivo `docker-compose.backup-volume.override.yml` para montar `./data/backups:/app/backups`.
   - Evita perder os ZIPs de backup quando o backend é recriado com `--force-recreate`.

2. **Backup automático diário**
   - Novo serviço interno `backup_scheduler.py`.
   - Ativável por variáveis de ambiente.
   - Gera backup do PostgreSQL automaticamente quando não houver backup recente.

3. **Validade do backup no healthcheck**
   - O sistema passa a avaliar idade do último backup.
   - Warning padrão se último backup tiver mais de 24h.
   - Error padrão se último backup tiver mais de 168h.

4. **Saneamento de erros históricos**
   - Erros antigos de notificação podem ser arquivados sem apagar histórico.
   - O healthcheck passa a considerar apenas erros ativos não arquivados.
   - Mantém rastreabilidade por `archived_at`, `archived_by` e `archive_reason`.

5. **Tela /admin/maintenance atualizada**
   - Status de validade do backup.
   - Status do backup automático.
   - Botão “Executar backup automático agora”.
   - Bloco “Saneamento de erros de notificação”.

## Variáveis recomendadas

```env
BACKUP_DIR=/app/backups
AUTO_BACKUP_ENABLED=true
AUTO_BACKUP_INTERVAL_HOURS=24
AUTO_BACKUP_CHECK_EVERY_MINUTES=60
AUTO_BACKUP_INCLUDE_MINIO=false
AUTO_BACKUP_MINIO_MAX_OBJECTS=5000
BACKUP_WARNING_HOURS=24
BACKUP_ERROR_HOURS=168
```

## Aplicação recomendada com volume persistente

```bash
docker compose -f docker-compose.yml -f docker-compose.backup-volume.override.yml up -d --build --force-recreate backend frontend
```

Depois acesse:

```text
http://localhost:3000/admin/maintenance
http://localhost:3000/admin/system-health
```

## Novas rotas

```text
GET  /maintenance/backup-freshness
GET  /maintenance/auto-backup/status
POST /maintenance/auto-backup/run
POST /maintenance/archive-notification-errors
```

## Fluxo recomendado

1. Aplicar com o override de volume.
2. Acessar `/admin/maintenance`.
3. Executar **backup automático agora**.
4. Rodar **saneamento de erros** primeiro em simulação.
5. Se o resultado estiver correto, executar o arquivamento real.
6. Abrir `/admin/system-health` e rodar novo healthcheck.

## Observação

O arquivamento de erro não exclui logs. Apenas marca erros históricos como arquivados para que o healthcheck não trate falhas antigas de teste como falha atual de produção.
