#!/usr/bin/env sh
set -eu

mkdir -p backups
backup_name="backups/cement_store-$(date +%Y-%m-%d_%H-%M-%S).db"
docker run --rm \
  -v cement-store-data:/data:ro \
  -v "$(pwd)/backups:/backup" \
  alpine:3.20 \
  cp /data/cement_store.db "/backup/$(basename "$backup_name")"
echo "Backup saved to $backup_name"
