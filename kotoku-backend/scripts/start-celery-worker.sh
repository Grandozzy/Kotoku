#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
  echo "Refusing to start Celery as root. Use the Dockerfile app user or configure the platform worker to run as a non-root user." >&2
  exit 1
fi

exec celery -A config worker --beat --loglevel=info --concurrency=2
