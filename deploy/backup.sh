#!/bin/sh
# Nightly backup: run from cron (see docs/DEPLOY.md).
set -e
cd "$(dirname "$0")"
docker compose exec -T web python tools/backup.py /backups
# keep 30 days on the server
find ./backups -name 'johanna-*.tar.gz' -mtime +30 -delete
# Optional: also copy off the server, e.g. with rclone to Backblaze B2 / Google Drive:
# rclone copy ./backups remote:johanna-backups --max-age 2d
