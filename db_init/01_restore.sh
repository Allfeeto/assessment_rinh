#!/bin/bash
set -e

echo "Restoring assessment_rinh database from dump..."

pg_restore \
  -U "$POSTGRES_USER" \
  -d "$POSTGRES_DB" \
  --no-owner \
  --no-privileges \
  /docker-entrypoint-initdb.d/assessment_DB_docker1.backup

echo "Database restore completed."