#!/bin/sh
# Nightly backup for the backup container, both encrypted with BACKUP_PASSPHRASE:
#   backups/sefername-YYYY-MM-DD.dump.enc   the database (pg_dump, custom format)
#   backups/uploads-YYYY-MM-DD.tar.enc      the uploaded files (already encrypted one by one with
#                                           DATA_ENCRYPTION_KEY; this adds a second lock on the archive)
# A backup copied off the server is useless to whoever finds it without the passphrase.
# Restore: see deploy/README.md, section 6.
set -eu
set -o pipefail

: "${BACKUP_PASSPHRASE:?Set BACKUP_PASSPHRASE in deploy/.env}"

# The postgres image has no openssl command; fetched once when the container starts
command -v openssl >/dev/null 2>&1 || apk add --no-cache openssl >/dev/null

encrypt() {
  # AES-256 with a key stretched from the passphrase (PBKDF2, many rounds: slow to guess)
  openssl enc -aes-256-cbc -pbkdf2 -iter 600000 -salt -pass env:BACKUP_PASSPHRASE -out "$1"
}

while true; do
  stamp=$(date +%F)

  db="/backups/sefername-${stamp}.dump.enc"
  if pg_dump --format=custom | encrypt "${db}.part"; then
    mv "${db}.part" "${db}"
    echo "database backup written: ${db}"
  else
    rm -f "${db}.part"
    echo "database backup FAILED at $(date)" >&2
  fi

  files="/backups/uploads-${stamp}.tar.enc"
  if tar -cf - -C /uploads . | encrypt "${files}.part"; then
    mv "${files}.part" "${files}"
    echo "uploads backup written: ${files}"
  else
    rm -f "${files}.part"
    echo "uploads backup FAILED at $(date)" >&2
  fi

  # Keep the last KEEP_DAYS days
  find /backups \( -name 'sefername-*.dump*' -o -name 'uploads-*.tar*' \) -mtime +"${KEEP_DAYS:-14}" -delete
  sleep 86400
done
