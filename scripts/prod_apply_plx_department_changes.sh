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

run_django_check_script='
from django.db import connection
from disciplines.models import ProgramDiscipline
from teachers.models import Teacher

connection.ensure_connection()
fields = {field.name: field for field in ProgramDiscipline._meta.get_fields()}
assert "discipline_code" in fields, "ProgramDiscipline.discipline_code missing"
assert "department" in fields, "ProgramDiscipline.department missing"
assert "is_active_in_plan" in fields, "ProgramDiscipline.is_active_in_plan missing"
assert hasattr(Teacher, "departments"), "Teacher.departments missing"

tables = set(connection.introspection.table_names())
assert "teacher_departments" in tables, "teacher_departments table missing"

missing = 0
for teacher in Teacher.objects.exclude(department_id__isnull=True).prefetch_related("departments"):
    if teacher.department_id not in {department.id for department in teacher.departments.all()}:
        missing += 1
assert missing == 0, f"{missing} teachers lost primary department M2M membership"

print("PLX department schema check OK")
'

[ -f manage.py ] || fail "Run this script from the project root containing manage.py"
[ -f docker-compose.yml ] || log "docker-compose.yml not found; direct mode may still work"

mode=${APPLY_MODE:-auto}
if [ "$mode" = "auto" ]; then
    if command -v docker >/dev/null 2>&1 && docker compose ps -q web >/dev/null 2>&1; then
        mode=docker
    else
        mode=direct
    fi
fi

backup_dir=${BACKUP_DIR_HOST:-backups/pre_migration}
backup_name="plx_department_changes_$(date +%Y%m%d_%H%M%S).dump"
mkdir -p "$backup_dir"

case "$mode" in
    docker)
        require_command docker
        log "Using Docker Compose mode"
        web_container=$(docker compose ps -q web || true)
        [ -n "$web_container" ] || fail "Docker service 'web' is not running"

        log "Checking Django and database connection"
        docker compose exec -T web sh -c \
            'DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py shell -c "from django.db import connection; connection.ensure_connection(); print(connection.vendor)"'

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

        log "Running Django migrations"
        docker compose exec -T web sh -c \
            'DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py migrate'

        log "Running Django checks"
        docker compose exec -T web sh -c \
            'DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py check'
        docker compose exec -T web sh -c \
            'DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py check_db_schema --live'

        log "Running post-migration schema validation"
        docker compose exec -T web sh -c \
            "DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py shell -c '$run_django_check_script'"
        ;;
    direct)
        require_command python
        require_command pg_dump
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

        log "Checking Django and database connection"
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py shell -c \
            "from django.db import connection; connection.ensure_connection(); print(connection.vendor)"

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

        log "Running Django migrations"
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py migrate

        log "Running Django checks"
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py check
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py check_db_schema --live

        log "Running post-migration schema validation"
        DJANGO_ENABLE_LOCAL_MIGRATIONS=1 python manage.py shell -c "$run_django_check_script"
        ;;
    *)
        fail "Unknown APPLY_MODE=$mode. Use auto, docker, or direct."
        ;;
esac

log "Completed PLX department changes. Backup: $backup_dir/$backup_name"
