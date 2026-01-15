#!/usr/bin/env bash
SRC="/root/example.sql"
DST="Linode:testing-singapore-2"
RCLONE_CMD=(rclone copy "$SRC" "$DST" \
  --progress --transfers 1 --s3-force-path-style \
  --s3-upload-cutoff 64M --s3-chunk-size 512M \
  --s3-upload-concurrency 4 --retries 10 --low-level-retries 20 \
  --timeout 1h --contimeout 1m)

while true; do
  echo "[$(date)] Starting rclone upload..."
  "${RCLONE_CMD[@]}"
  RC=$?
  if [ "$RC" -eq 0 ]; then
    echo "[$(date)] Upload completed successfully."
    break
  fi
  echo "[$(date)] rclone exited with code $RC. Retrying in 30 seconds..."
  sleep 30
 done
