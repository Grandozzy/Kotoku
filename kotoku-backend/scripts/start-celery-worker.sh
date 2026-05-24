#!/bin/sh
set -eu

exec celery -A kotoku_backend worker --loglevel=info --concurrency=2
