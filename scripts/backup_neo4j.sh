#!/usr/bin/env bash
# Backup Neo4j database via neo4j-admin dump.
# Usage: ./scripts/backup_neo4j.sh
# Requires: NEO4J_HOME environment variable or neo4j-admin on PATH

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_NAME="${NEO4J_DATABASE:-neo4j}"
BACKUP_FILE="${BACKUP_DIR}/cfd_neo4j_${TIMESTAMP}.dump"

NEO4J_ADMIN="${NEO4J_HOME:+${NEO4J_HOME}/bin/}neo4j-admin"

if ! command -v "$NEO4J_ADMIN" &> /dev/null; then
    echo "ERROR: neo4j-admin not found."
    echo "Set NEO4J_HOME or ensure neo4j-admin is on PATH."
    exit 1
fi

mkdir -p "$BACKUP_DIR"

echo "Starting Neo4j backup (database: $DB_NAME)..."
$NEO4J_ADMIN database dump "$DB_NAME" --to-path="$BACKUP_FILE"

echo "Backup complete: $BACKUP_FILE"
echo "Size: $(du -h "$BACKUP_FILE" | cut -f1)"
