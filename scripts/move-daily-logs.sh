#!/bin/bash
# Move daily heartbeat logs from memory/ to archive/ to prevent search noise.
# Only moves yesterday's and older files — today's file is left alone (lobster is writing to it).
#
# Usage:
#   chmod +x move-daily-logs.sh
#   ./move-daily-logs.sh
#
# Cron (daily at 6am):
#   0 6 * * * $HOME/move-daily-logs.sh
#
# Author: KingMaker
# License: MIT

MEMORY_DIR=$HOME/.openclaw/workspace/memory
ARCHIVE_DIR=$HOME/.openclaw/workspace/daily-archive
TODAY=$(date +%Y-%m-%d)

mkdir -p "$ARCHIVE_DIR"

for f in "$MEMORY_DIR"/20[0-9][0-9]-[0-9][0-9]-[0-9][0-9].md; do
    [ -f "$f" ] || continue
    FILENAME=$(basename "$f" .md)
    # Skip today's file (lobster is actively writing to it)
    [ "$FILENAME" = "$TODAY" ] && continue
    mv "$f" "$ARCHIVE_DIR/" 2>/dev/null
done
