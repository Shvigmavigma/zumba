#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKUP_ROOT="${1:-backups}"
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"
BACKUP_DIR="$PROJECT_ROOT/$BACKUP_ROOT/bmrl-$TIMESTAMP"
TEMP_DIR="$PROJECT_ROOT/$BACKUP_ROOT/.bmrl-$TIMESTAMP.tmp"

cd "$PROJECT_ROOT"
mkdir -p "$PROJECT_ROOT/$BACKUP_ROOT"

compose() {
  sudo docker compose "$@"
}

cleanup() {
  if [[ -d "$TEMP_DIR" ]]; then
    rm -rf -- "$TEMP_DIR"
  fi
}
trap cleanup EXIT

mkdir -p "$TEMP_DIR"
compose up -d postgres backend
until compose exec -T postgres sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1; do
  sleep 1
done

compose exec -T postgres sh -lc 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner --no-privileges' > "$TEMP_DIR/database.dump"
compose exec -T backend sh -lc 'tar -czf - -C /app/uploads .' > "$TEMP_DIR/uploads.tar.gz"
cp docker-compose.yml .env.example "$TEMP_DIR/"
{
  printf 'created_at_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  printf 'git_revision=%s\n' "$(git rev-parse HEAD 2>/dev/null || printf unknown)"
  printf 'database=database.dump\n'
  printf 'uploads=uploads.tar.gz\n'
  printf 'database_sha256=%s\n' "$(sha256sum "$TEMP_DIR/database.dump" | awk '{print $1}')"
  printf 'uploads_sha256=%s\n' "$(sha256sum "$TEMP_DIR/uploads.tar.gz" | awk '{print $1}')"
} > "$TEMP_DIR/manifest.txt"

mv "$TEMP_DIR" "$BACKUP_DIR"
trap - EXIT
printf 'Backup created: %s\n' "$BACKUP_DIR"
printf 'Do not delete the project until database.dump and uploads.tar.gz are verified.\n'
