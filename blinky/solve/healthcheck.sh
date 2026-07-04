#!/usr/bin/env bash
# healthcheck.sh -- verify a Blinky challenge instance is up AND solvable.
#
# Runs the reference solver (solve.py), which submits the reference exploit to the
# server and reads the response back. Exits 0 iff a flag comes back -- suitable as
# a platform healthcheck / SLA probe.
#
#   SERVER=http://host:port ./healthcheck.sh      # default http://127.0.0.1:8080
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SERVER="${SERVER:-http://127.0.0.1:8080}"

echo "[healthcheck] target: $SERVER"
if python3 "$HERE/solve.py"; then
    echo "[healthcheck] OK -- instance is up and solvable"
    exit 0
else
    echo "[healthcheck] FAIL -- no flag returned (see output above)"
    exit 1
fi
