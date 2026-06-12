#!/bin/sh
set -eu

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

load_env_file() {
    if [ -f .env ]; then
        set -a
        # shellcheck disable=SC1091
        . ./.env
        set +a
    fi
}

run_schema_check='
from django.db import connection
from competencies.models import CompetenceIndicator, CompetenceIndicatorImport

connection.ensure_connection()
tables = set(connection.introspection.table_names())
assert "competence_indicator" in tables, "competence_indicator table missing"
assert "competence_indicator_import" in tables, "competence_indicator_import table missing"

required_objects = {
    "comp_ind_imp_prog_date_idx",
    "comp_ind_imp_sha_idx",
    "comp_ind_imp_status_idx",
    "comp_indicator_code_idx",
    "comp_indicator_competence_idx",
    "competence_indicator_competence_code_key",
    "competence_indicator_import_counts_check",
    "competence_indicator_import_status_check",
    "competence_indicator_source_row_check",
    "competence_indicator_source_table_check",
}
found = set()
with connection.cursor() as cursor:
    for table in ("competence_indicator", "competence_indicator_import"):
        found.update(connection.introspection.get_constraints(cursor, table).keys())
missing = required_objects - found
assert not missing, f"competence indicator DB objects missing: {sorted(missing)}"

assert CompetenceIndicator._meta.db_table == "competence_indicator"
assert CompetenceIndicatorImport._meta.db_table == "competence_indicator_import"
print("Competence indicator schema check OK")
'

required_migrations_check='
from django.db import connection
from django.db.migrations.recorder import MigrationRecorder

applied = set(MigrationRecorder(connection).applied_migrations())
required = {
    ("disciplines", "0002_program_discipline_active_in_plan"),
    ("teachers", "0001_teacher_departments"),
}
missing = required - applied
assert not missing, (
    "Required previously applied PLX/department migrations are not recorded: "
    f"{sorted(missing)}. Apply or reconcile them separately; this script will not replay them."
)
print("Required previous migrations are recorded")
'

[ -f manage.py ] || fail "Run this script from the project root containing manage.py"

mode=${APPLY_MODE:-auto}
if [ "$mode" = "auto" ]; then
    if command -v docker >/dev/null 2>&1 && docker compose ps -q web >/dev/null 2>&1; then
        mode=docker
    else
        mode=direct
    fi
fi

backup_dir=${BACKUP_DIR_HOST:-backups/pre_migration}
backup_name="competence_indicator_changes_$(date +%Y%m%d_%H%M%S).dump"
mkdir -p "$backup_dir"

case "$mode" in
    docker)
        require_command docker
        log "Using Docker Compose mode"
        web_container=$(docker compose ps -q web || true)
        [ -n "$web_container" ] || fail "Docker service 'web' is not running"

        log "Checking DOC converter and database connection"
        docker compose exec -T web sh -c \
            'command -v soffice >/dev/null 2>&1 || command -v libreoffice >/dev/null 2>&1'
        docker compose exec -T web sh -c \
            'DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print(connection.vendor)"'
        docker compose exec -T web sh -c \
            "DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py shell -c '$required_migrations_check'"

        log "Creating PostgreSQL backup: $backup_dir/$backup_name"
        docker compose run --rm \
            -v "$(pwd)/$backup_dir:/manual-backups" \
            db-backup sh -c "
                set -eu
                : \"\${POSTGRES_DB:=\${DB_NAME:-}}\"
                : \"\${POSTGRES_USER:=\${DB_USER:-}}\"
                : \"\${POSTGRES_PASSWORD:=\${DB_PASSWORD:-}}\"
                [ -n \"\$POSTGRES_DB\" ] || { echo 'POSTGRES_DB or DB_NAME is required' >&2; exit 1; }
                [ -n \"\$POSTGRES_USER\" ] || { echo 'POSTGRES_USER or DB_USER is required' >&2; exit 1; }
                [ -n \"\$POSTGRES_PASSWORD\" ] || { echo 'POSTGRES_PASSWORD or DB_PASSWORD is required' >&2; exit 1; }
                PGPASSWORD=\"\$POSTGRES_PASSWORD\" pg_dump \
                    --host=\"\${BACKUP_DB_HOST:-\${DB_HOST:-db}}\" \
                    --port=\"\${BACKUP_DB_PORT:-\${DB_PORT:-5432}}\" \
                    --username=\"\$POSTGRES_USER\" \
                    --dbname=\"\$POSTGRES_DB\" \
                    --format=custom \
                    --no-owner \
                    --no-privileges \
                    --file=\"/manual-backups/$backup_name\"
                test -s \"/manual-backups/$backup_name\"
            "

        log "Applying competencies migration"
        docker compose exec -T web sh -c \
            'DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py migrate competencies'

        log "Running Django and schema checks"
        docker compose exec -T web sh -c \
            'DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py check'
        docker compose exec -T web sh -c \
            'DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py check_db_schema --live'
        docker compose exec -T web sh -c \
            "DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py shell -c '$run_schema_check'"
        ;;
    direct)
        require_command python
        require_command pg_dump
        if command -v soffice >/dev/null 2>&1 || command -v libreoffice >/dev/null 2>&1; then
            log "LibreOffice DOC converter is available"
        elif command -v powershell.exe >/dev/null 2>&1; then
            log "Checking Microsoft Word DOC converter"
            powershell.exe -NoProfile -NonInteractive -Command \
                '$word = $null; try { $word = New-Object -ComObject Word.Application; $word.Visible = $false; $word.DisplayAlerts = 0 } finally { if ($null -ne $word) { $word.Quit(); [void][System.Runtime.InteropServices.Marshal]::FinalReleaseComObject($word) } }' \
                >/dev/null || fail "Microsoft Word COM converter is not available"
        else
            fail "LibreOffice or Microsoft Word is required for .doc imports in direct mode"
        fi
        log "Using direct host mode"
        load_env_file

        POSTGRES_DB=${POSTGRES_DB:-${DB_NAME:-}}
        POSTGRES_USER=${POSTGRES_USER:-${DB_USER:-}}
        POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-${DB_PASSWORD:-}}
        DB_HOST=${DB_HOST:-localhost}
        DB_PORT=${DB_PORT:-5432}
        [ -n "$POSTGRES_DB" ] || fail "POSTGRES_DB or DB_NAME is required for backup"
        [ -n "$POSTGRES_USER" ] || fail "POSTGRES_USER or DB_USER is required for backup"
        [ -n "$POSTGRES_PASSWORD" ] || fail "POSTGRES_PASSWORD or DB_PASSWORD is required for backup"

        log "Checking database connection"
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py shell -c \
            "from django.db import connection; connection.ensure_connection(); print(connection.vendor)"
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py shell -c "$required_migrations_check"

        log "Creating PostgreSQL backup: $backup_dir/$backup_name"
        PGPASSWORD=$POSTGRES_PASSWORD pg_dump \
            --host="$DB_HOST" \
            --port="$DB_PORT" \
            --username="$POSTGRES_USER" \
            --dbname="$POSTGRES_DB" \
            --format=custom \
            --no-owner \
            --no-privileges \
            --file="$backup_dir/$backup_name"
        [ -s "$backup_dir/$backup_name" ] || fail "pg_dump produced an empty backup"

        log "Applying competencies migration"
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py migrate competencies

        log "Running Django and schema checks"
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py check
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py check_db_schema --live
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py shell -c "$run_schema_check"
        ;;
    *)
        fail "Unknown APPLY_MODE=$mode. Use auto, docker, or direct."
        ;;
esac

log "Completed competence indicator changes. Backup: $backup_dir/$backup_name"
