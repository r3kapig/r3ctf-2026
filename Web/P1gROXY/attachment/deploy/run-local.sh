#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

load_defaults() {
  file="$1"
  [ -f "$file" ] || return 0
  while IFS='=' read -r key value; do
    case "$key" in
      ''|\#*) continue ;;
    esac
    current="$(eval "printf '%s' \"\${$key:-}\"")"
    if [ -z "$current" ]; then
      export "$key=$value"
    fi
  done < "$file"
}

load_defaults deploy/p1groxy.env
load_defaults deploy/warehousehub.env

if [ ! -x services/proxy/bin/P1gROXY ]; then
  make
fi

if [ -d services/warehousehub/.venv ]; then
  # shellcheck disable=SC1091
  . services/warehousehub/.venv/bin/activate
fi

if command -v gunicorn >/dev/null 2>&1; then
  gunicorn \
    --chdir services/warehousehub \
    --bind "${WAREHOUSEHUB_BIND:-127.0.0.1:15081}" \
    --workers "${WAREHOUSEHUB_WORKERS:-2}" \
    --access-logfile - \
    "app.app:app" &
else
  WAREHOUSEHUB_PORT="${WAREHOUSEHUB_BIND##*:}"
  PYTHONPATH=services/warehousehub python3 -m flask --app app.app:app run --host 127.0.0.1 --port "$WAREHOUSEHUB_PORT" &
fi
WEB_PID=$!

cleanup() {
  kill "$WEB_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

sleep 1
exec services/proxy/bin/P1gROXY
