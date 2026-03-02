#!/usr/bin/env bash
# Backup Supabase PostgreSQL database via pg_dump.
# Usage: ./scripts/backup_postgres.sh
# Requires: DATABASE_URL environment variable (Supabase connection string)

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/cfd_postgres_${TIMESTAMP}.sql.gz"

if [ -z "${DATABASE_URL:-}" ]; then
    echo "ERROR: DATABASE_URL environment variable is not set."
    echo "Set it to your Supabase PostgreSQL connection string."
    exit 1
fi

mkdir -p "$BACKUP_DIR"

echo "Starting PostgreSQL backup..."
pg_dump "$DATABASE_URL" --no-owner --no-privileges | gzip > "$BACKUP_FILE"

echo "Backup complete: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
