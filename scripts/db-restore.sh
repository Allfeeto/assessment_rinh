#!/bin/sh
set -eu

usage() {
    echo "Usage: $0 /backups/weekly/weekly.dump|/backups/monthly/monthly.dump" >&2
}

log() {
    printf '%s %s\n' "$(date -Iseconds)" "$*"
}

fail() {
    log "ERROR: $*"
    exit 1
}

backup_file=${1:-}
if [ -z "$backup_file" ]; then
    usage
    exit 2
fi

[ -f "$backup_file" ] || fail "Backup file does not exist: $backup_file"
[ -s "$backup_file" ] || fail "Backup file is empty: $backup_file"

POSTGRES_DB=${POSTGRES_DB:-${DB_NAME:-}}
POSTGRES_USER=${POSTGRES_USER:-${DB_USER:-}}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}

: "${POSTGRES_DB:?POSTGRES_DB or DB_NAME is required}"
: "${POSTGRES_USER:?POSTGRES_USER or DB_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD or DB_PASSWORD is required}"

db_host=${BACKUP_DB_HOST:-${DB_HOST:-db}}
db_port=${BACKUP_DB_PORT:-${DB_PORT:-5432}}

log "Restoring PostgreSQL database $POSTGRES_DB from $backup_file"

PGPASSWORD=$POSTGRES_PASSWORD pg_restore \
    --host="$db_host" \
    --port="$db_port" \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --clean \
    --if-exists \
    --no-owner \
    --no-privileges \
    "$backup_file"

log "Restore completed from $backup_file"
