#!/usr/bin/env bash
# Daily PostgreSQL backup: dump → gzip → (optional) upload to external storage.
#
# Local dumps go to ./backups and are pruned after $BACKUP_RETENTION_DAYS.
# To upload off-site, set BACKUP_RCLONE_REMOTE in .env (e.g. "s3:my-bucket/clipresumen")
# and install/configure rclone on the host (https://rclone.org).
#
# Schedule it daily via cron (see README → Backups):
#   0 3 * * *  /opt/clipresumen/backup.sh >> /var/log/clipresumen-backup.log 2>&1
#
set -euo pipefail
cd "$(dirname "$0")"

set -a
# shellcheck disable=SC1091
[ -f .env ] && . ./.env
set +a

COMPOSE="docker compose -f docker-compose.prod.yml"
DB_USER="${POSTGRES_USER:-clipresumen}"
DB_NAME="${POSTGRES_DB:-clipresumen}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"

mkdir -p ./backups
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="./backups/${DB_NAME}-${STAMP}.sql.gz"

echo "==> Dumping ${DB_NAME} → ${OUT}"
$COMPOSE exec -T postgres pg_dump -U "${DB_USER}" "${DB_NAME}" | gzip > "${OUT}"

# Optional off-site upload.
if [ -n "${BACKUP_RCLONE_REMOTE:-}" ]; then
  echo "==> Uploading to ${BACKUP_RCLONE_REMOTE}"
  rclone copy "${OUT}" "${BACKUP_RCLONE_REMOTE}"
fi

echo "==> Pruning local backups older than ${RETENTION_DAYS} days"
find ./backups -name "*.sql.gz" -mtime "+${RETENTION_DAYS}" -delete

echo "==> Backup complete"
