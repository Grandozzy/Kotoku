#!/usr/bin/env bash
set -euo pipefail

python - <<'PY'
import os
import socket
import time

host = os.getenv("DB_HOST", "127.0.0.1")
port = int(os.getenv("DB_PORT", "5432"))

for attempt in range(30):
    with socket.socket() as sock:
        sock.settimeout(1)
        try:
            sock.connect((host, port))
        except OSError:
            time.sleep(1)
            continue
    print(f"database reachable at {host}:{port}")
    break
else:
    raise SystemExit(f"database not reachable at {host}:{port}")
PY
