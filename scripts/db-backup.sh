#!/bin/sh
set -eu

usage() {
    echo "Usage: $0 weekly|monthly" >&2
}

log() {
    printf '%s %s\n' "$(date -Iseconds)" "$*"
}

fail() {
    log "ERROR: $*"
    exit 1
}

require_command() {
    command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

require_env() {
    eval "value=\${$1:-}"
    [ -n "$value" ] || fail "Required environment variable is empty: $1"
}

prepare_dir() {
    dir=$1
    umask 077
    mkdir -p "$dir"
    chmod 700 "$dir"
}

backup_kind=${1:-}
case "$backup_kind" in
    weekly|monthly) ;;
    *)
        usage
        exit 2
        ;;
esac

require_command pg_dump

POSTGRES_DB=${POSTGRES_DB:-${DB_NAME:-}}
POSTGRES_USER=${POSTGRES_USER:-${DB_USER:-}}
POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}

require_env POSTGRES_DB
require_env POSTGRES_USER
require_env POSTGRES_PASSWORD

backup_root=${BACKUP_DIR:-/backups}
backup_dir="$backup_root/$backup_kind"
backup_file="$backup_dir/$backup_kind.dump"
tmp_file="$backup_dir/.$backup_kind.dump.tmp.$$"
lock_dir="$backup_root/.$backup_kind.lock"

cleanup() {
    rm -f "$tmp_file"
    if [ "${lock_acquired:-0}" = "1" ]; then
        rmdir "$lock_dir" 2>/dev/null || true
    fi
}
trap cleanup EXIT INT TERM

prepare_dir "$backup_root"
prepare_dir "$backup_dir"

if ! mkdir "$lock_dir" 2>/dev/null; then
    fail "Another $backup_kind backup is already running"
fi
lock_acquired=1

db_host=${BACKUP_DB_HOST:-${DB_HOST:-db}}
db_port=${BACKUP_DB_PORT:-${DB_PORT:-5432}}

log "Starting $backup_kind PostgreSQL backup to $backup_file"

PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
    --host="$db_host" \
    --port="$db_port" \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --format=custom \
    --no-owner \
    --no-privileges \
    --file="$tmp_file"

[ -s "$tmp_file" ] || fail "pg_dump produced an empty backup file"

chmod 600 "$tmp_file"
mv -f "$tmp_file" "$backup_file"
chmod 600 "$backup_file"

log "Completed $backup_kind PostgreSQL backup: $backup_file ($(wc -c < "$backup_file") bytes)"
