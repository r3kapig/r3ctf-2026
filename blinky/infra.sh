#!/usr/bin/env bash
# infra.sh -- build + run the Blinky challenge server (R3CTF).
#
#   ./infra.sh build          docker build the image
#   ./infra.sh run            docker run it (foreground) on $PORT (default 8080)
#   ./infra.sh local          run the server WITHOUT docker (needs python3 +
#                             mips64el binutils on the host) -- for dev/testing
#   ./infra.sh health         run the reference solver against a running instance
#
# Env: NAME (image name), PORT, FLAG (dynamic flag to bake), SERVER (health URL).
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NAME="${NAME:-blinky}"
PORT="${PORT:-8080}"
REG="${REG:-registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700}"

cmd="${1:-run}"
case "$cmd" in
  build)
    docker build -f "$HERE/deploy/Dockerfile" -t "$REG/$NAME:latest" "$HERE"
    ;;
  run)
    docker run --rm -p "$PORT:8080" \
      ${FLAG:+-e FLAG="$FLAG"} \
      --name "$NAME" "$REG/$NAME:latest"
    ;;
  local)
    # Dev mode: bake the flag, then run the stdlib server directly.
    FLAG="${FLAG-}"; [ -n "$FLAG" ] || FLAG='R3CTF{TEST_FLGA}'
    FLAG="$FLAG" OUT="$HERE/deploy/server/kernel_template.mem" "$HERE/deploy/server/build_kernel.sh"
    exec env PORT="$PORT" python3 "$HERE/deploy/server/server.py"
    ;;
  health)
    SERVER="${SERVER:-http://127.0.0.1:$PORT}" exec "$HERE/solve/healthcheck.sh"
    ;;
  *)
    echo "usage: $0 {build|run|local|health}" >&2; exit 2 ;;
esac
