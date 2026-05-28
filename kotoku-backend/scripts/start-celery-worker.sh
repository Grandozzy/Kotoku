#!/bin/sh
set -eu

exec celery -A config worker --beat --loglevel=info --concurrency=2
