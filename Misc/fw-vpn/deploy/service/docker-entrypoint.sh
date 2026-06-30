#!/bin/sh
set -eu

if [ -z "${SSLVPN_USER:-}" ]; then
    SSLVPN_USER=ops
fi

if [ -z "${SSLVPN_PASS:-}" ]; then
    SSLVPN_PASS="$(dd if=/dev/urandom bs=32 count=1 2>/dev/null | base64 | tr -dc 'A-Za-z0-9' | head -c 6)"
    echo "[entrypoint] generated random SSLVPN_PASS for this container start"
fi

export SSLVPN_USER SSLVPN_PASS
exec "$@"
