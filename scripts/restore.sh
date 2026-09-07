#!/bin/sh
# Restaura um backup criado por backup.sh para o Postgres que já está a
# correr (docker compose up). APAGA os dados atuais antes de restaurar -
# confirma sempre antes de correr isto em produção.
#
# Uso (a partir da pasta do projeto, fora do container):
#   docker compose run --rm -v "$(pwd)/backups:/backups" postgres \
#       sh /backups/../scripts/restore.sh evolure_20260830_120000.sql.gz
#
# Mais simples, correndo dentro do container backup já existente:
#   docker compose exec backup sh /scripts/restore.sh evolure_20260830_120000.sql.gz
set -e

if [ -z "$1" ]; then
    echo "Uso: restore.sh <nome-do-ficheiro.sql.gz>"
    echo "Backups disponíveis:"
    ls -la /backups/*.sql.gz 2>/dev/null || echo "  (nenhum backup encontrado em /backups)"
    exit 1
fi

FILE="/backups/$1"
if [ ! -f "${FILE}" ]; then
    echo "Ficheiro não encontrado: ${FILE}"
    exit 1
fi

echo "ATENÇÃO: isto vai APAGAR a base de dados atual (${POSTGRES_DB}) e substituir pelo backup."
echo "Backup a restaurar: ${FILE}"
printf "Confirma escrevendo 'sim': "
read -r CONFIRM
if [ "${CONFIRM}" != "sim" ]; then
    echo "Cancelado."
    exit 1
fi

echo "$(date '+%Y-%m-%d %H:%M:%S') - A restaurar..."
gunzip -c "${FILE}" | psql -h postgres -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"
echo "$(date '+%Y-%m-%d %H:%M:%S') - Restauro concluído."
