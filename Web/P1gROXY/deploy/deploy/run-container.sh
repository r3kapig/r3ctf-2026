#!/usr/bin/env sh
set -u

export P1GROXY_LISTEN_HOST="${P1GROXY_LISTEN_HOST:-0.0.0.0}"
export P1GROXY_LISTEN_PORT="${P1GROXY_LISTEN_PORT:-8080}"
export P1GROXY_UPSTREAM_HOST="${P1GROXY_UPSTREAM_HOST:-127.0.0.1}"
export P1GROXY_UPSTREAM_PORT="${P1GROXY_UPSTREAM_PORT:-15081}"
export P1GROXY_CACHE_CAPACITY_BYTES="${P1GROXY_CACHE_CAPACITY_BYTES:-65536}"
export WAREHOUSEHUB_WORKERS="${WAREHOUSEHUB_WORKERS:-1}"
export MALLOC_CHECK_="${MALLOC_CHECK_:-0}"

gunicorn \
  --chdir /opt/p1groxy/services/warehousehub \
  --bind "127.0.0.1:${P1GROXY_UPSTREAM_PORT}" \
  --workers "${WAREHOUSEHUB_WORKERS}" \
  --access-logfile - \
  "app.app:app" &
WEB_PID=$!
PROXY_PID=""

cleanup() {
  kill "$WEB_PID" ${PROXY_PID:+"$PROXY_PID"} 2>/dev/null || true
}
trap 'cleanup; exit 0' INT TERM EXIT

sleep 1
cd /tmp || exit 1

while :; do
  /opt/p1groxy/services/proxy/bin/P1gROXY &
  PROXY_PID=$!
  wait "$PROXY_PID" || true
  sleep 0.2
done
