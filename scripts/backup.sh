#!/usr/bin/env bash
# backup.sh - create a timestamped, verified .tar.gz backup of a directory
#             and keep only the newest N backups (retention).
#
# Usage:  ./scripts/backup.sh <source_dir> [backup_dir] [keep]
# Cron:   0 2 * * * /opt/task-tracker/scripts/backup.sh /opt/task-tracker/data /var/backups/task-tracker 7

set -euo pipefail

SRC="${1:?Usage: $0 <source_dir> [backup_dir] [keep]}"
DEST="${2:-./backups}"
KEEP="${3:-5}"

log() { printf '%s [backup] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

if [[ ! -d "$SRC" ]]; then
  log "ERROR: source directory '$SRC' does not exist"
  exit 1
fi

mkdir -p "$DEST"
NAME="$(basename "$SRC")"
STAMP="$(date '+%Y%m%d_%H%M%S')"
ARCHIVE="$DEST/${NAME}_${STAMP}.tar.gz"

log "Backing up '$SRC' -> '$ARCHIVE'"
tar -czf "$ARCHIVE" -C "$(dirname "$SRC")" "$NAME"

# Verify the archive can be read back and record a checksum.
tar -tzf "$ARCHIVE" > /dev/null
sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"
FILES=$(tar -tzf "$ARCHIVE" | grep -vc '/$' || true)
SIZE=$(du -h "$ARCHIVE" | cut -f1)
log "Verified archive: $FILES files, $SIZE, sha256 saved"

# Retention: delete everything except the newest $KEEP backups.
mapfile -t OLD < <(find "$DEST" -maxdepth 1 -name "${NAME}_*.tar.gz" -printf '%T@ %p\n' \
                   | sort -rn | tail -n +"$((KEEP + 1))" | cut -d' ' -f2-)
for f in "${OLD[@]}"; do
  rm -f -- "$f" "$f.sha256"
  log "Retention: removed old backup $(basename "$f")"
done
COUNT=$(find "$DEST" -maxdepth 1 -name "${NAME}_*.tar.gz" | wc -l)
log "Done. $COUNT backup(s) kept in '$DEST' (limit $KEEP)"
