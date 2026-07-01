#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if docker compose version >/dev/null 2>&1; then
    DC="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
    DC="docker-compose"
else
    echo "[run] Docker Compose not found. Install the v2 plugin (docker compose) or the v1 binary (docker-compose)." >&2
    exit 1
fi

echo "[run] tearing down any existing stack (and its data)..."
$DC down -v >/dev/null 2>&1 || true

echo "[run] building and starting backend + victim..."
$DC up -d --build

echo "[run] waiting for the victim device to finish booting (first boot ~10-15 min)..."
for _ in $(seq 1 360); do
    $DC logs victim 2>/dev/null | grep -q READY && break
    sleep 10
done

if $DC logs victim 2>/dev/null | grep -q READY; then
    echo
    echo "[run] ready."
    echo "      backend:       http://localhost:8000"
    echo "      victim handle: victim"
    echo "      Register an account on the backend and send the victim a crafted DM."
else
    echo "[run] victim did not report READY in time; check: $DC logs victim"
    exit 1
fi
