#!/bin/sh

set -e

: "${FLAG:?FLAG environment variable is required}"

umask 077
printf '%s\n' "$FLAG" > /flag
chown root:root /flag
chmod 0400 /flag
unset FLAG

chmod 0444 /entrypoint.sh || true

EXTRA=""
[ "${R3CHAT_INSECURE_TLS:-}" = "1" ] && EXTRA="--ignore-certificate-errors"

echo "[bot] launching R3Chat once -> ${R3CHAT_HOST}:${R3CHAT_PORT}"
exec env -i \
  HOME=/home/bot \
  USER=bot \
  LOGNAME=bot \
  PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin \
  R3CHAT_BOT="${R3CHAT_BOT:-1}" \
  R3CHAT_HOST="${R3CHAT_HOST:-127.0.0.1}" \
  R3CHAT_PORT="${R3CHAT_PORT:-8443}" \
  R3CHAT_BOT_USER="${R3CHAT_BOT_USER:-}" \
  R3CHAT_INSECURE_TLS="${R3CHAT_INSECURE_TLS:-}" \
  ELECTRON_DISABLE_SANDBOX="${ELECTRON_DISABLE_SANDBOX:-1}" \
  setpriv --reuid=1001 --regid=1001 --init-groups \
  xvfb-run -a /opt/R3Chat/r3chat-client --no-sandbox $EXTRA "$@"
