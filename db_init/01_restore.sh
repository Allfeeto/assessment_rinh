#!/bin/bash
set -e

BACKUP_PATH=""

for candidate in \
  /docker-entrypoint-initdb.d/assessment_DB_docker2.backup \
  /docker-entrypoint-initdb.d/asssessment_DB_docker2.backup \
  /docker-entrypoint-initdb.d/assessment_DB_docker1.backup
do
  if [ -f "$candidate" ]; then
    BACKUP_PATH="$candidate"
    break
  fi
done

if [ -n "$BACKUP_PATH" ]; then
  echo "Restoring assessment_rinh database from dump: $BACKUP_PATH"

  pg_restore \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --no-owner \
    --no-privileges \
    "$BACKUP_PATH"

  echo "Database restore completed."
  exit 0
fi

echo "No database backup found. If you need SQL bootstrap, place a private *.sql file in db_init/."
exit 0
