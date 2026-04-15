#!/usr/bin/env bash
set -euo pipefail

./scripts/wait_for_db.sh
python manage.py migrate --noinput
python manage.py runserver 0.0.0.0:8000
