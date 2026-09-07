#!/bin/sh
# Corre em loop dentro do container `backup` (imagem postgres:16-alpine,
# já tem pg_dump). Grava em /backups, que está montado como bind mount
# para ./backups no teu disco - por isso sobrevive a `docker compose down -v`
# (que apaga volumes Docker, mas não pastas montadas do host).
set -e

mkdir -p /backups

INTERVAL_HOURS="${BACKUP_INTERVAL_HOURS:-24}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup automático a arrancar (a cada ${INTERVAL_HOURS}h, retenção de ${RETENTION_DAYS} dias)"

while true; do
    TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
    FILE="/backups/evolure_${TIMESTAMP}.sql.gz"

    echo "$(date '+%Y-%m-%d %H:%M:%S') - A criar backup: ${FILE}"
    if pg_dump -h postgres -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" | gzip > "${FILE}"; then
        SIZE=$(du -h "${FILE}" | cut -f1)
        echo "$(date '+%Y-%m-%d %H:%M:%S') - Backup concluído (${SIZE}): ${FILE}"
    else
        echo "$(date '+%Y-%m-%d %H:%M:%S') - FALHOU o backup - ficheiro incompleto removido"
        rm -f "${FILE}"
    fi

    # remove backups mais antigos que RETENTION_DAYS
    DELETED=$(find /backups -name "evolure_*.sql.gz" -mtime "+${RETENTION_DAYS}" -print -delete | wc -l)
    if [ "${DELETED}" -gt 0 ]; then
        echo "$(date '+%Y-%m-%d %H:%M:%S') - ${DELETED} backup(s) antigo(s) removido(s) (> ${RETENTION_DAYS} dias)"
    fi

    echo "$(date '+%Y-%m-%d %H:%M:%S') - Próximo backup em ${INTERVAL_HOURS}h"
    sleep "$((INTERVAL_HOURS * 3600))"
done
