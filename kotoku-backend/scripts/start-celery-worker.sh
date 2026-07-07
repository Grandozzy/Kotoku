#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
  echo "Refusing to start Celery as root. Use the Dockerfile app user or configure the platform worker to run as a non-root user." >&2
  exit 1
fi

# Fail fast if S3 credentials are missing — avoids silent SignatureDoesNotMatch at task time.
: "${AWS_ACCESS_KEY_ID:?AWS_ACCESS_KEY_ID is not set. Add it to the celery-worker Railway service variables.}"
: "${AWS_SECRET_ACCESS_KEY:?AWS_SECRET_ACCESS_KEY is not set. Add it to the celery-worker Railway service variables.}"
: "${AWS_STORAGE_BUCKET_NAME:?AWS_STORAGE_BUCKET_NAME is not set.}"

exec celery -A config worker --beat --loglevel=info --concurrency=2
