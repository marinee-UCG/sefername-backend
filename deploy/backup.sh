#!/bin/sh
# Nightly database dump for the backup container. Files: backups/sefername-YYYY-MM-DD.dump
# Restore one with:  pg_restore --clean --if-exists -d sefername /backups/<file>   (see README)
set -eu

while true; do
  stamp=$(date +%F)
  target="/backups/sefername-${stamp}.dump"
  if pg_dump --format=custom --file="${target}.part"; then
    mv "${target}.part" "${target}"
    echo "backup written: ${target}"
  else
    rm -f "${target}.part"
    echo "backup FAILED at $(date)" >&2
  fi
  # Keep the last KEEP_DAYS days
  find /backups -name 'sefername-*.dump' -mtime +"${KEEP_DAYS:-14}" -delete
  sleep 86400
done
