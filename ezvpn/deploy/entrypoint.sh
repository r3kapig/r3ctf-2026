#!/bin/sh
# eazyVPN runtime entrypoint.
#   1) pick up the platform-injected dynamic flag and drop it where the solve
#      paths can read it, then scrub the env (CTF-Archives idiom);
#   2) launch the self-listening TLS gateway on :4433.
#
# Supported flag env vars: $FLAG (CTFd / NSSCTF), $GZCTF_FLAG (GZCTF), $DASFLAG (DASCTF).
set -eu

# --- dynamic flag (CTF-Archives style) ---
if [ -n "${DASFLAG:-}" ]; then
    INSERT_FLAG="$DASFLAG"
elif [ -n "${FLAG:-}" ]; then
    INSERT_FLAG="$FLAG"
elif [ -n "${GZCTF_FLAG:-}" ]; then
    INSERT_FLAG="$GZCTF_FLAG"
else
    INSERT_FLAG="flag{TEST_Dynamic_FLAG}"
fi

DASFLAG=no_FLAG; FLAG=no_FLAG; GZCTF_FLAG=no_FLAG
export DASFLAG FLAG GZCTF_FLAG

printf '%s\n' "$INSERT_FLAG" | tee /flag /app/flag >/dev/null
chmod 444 /flag /app/flag  2>/dev/null || true

# --- VPN credentials: NO baked-in default. Random
: "${SSLVPN_USER:=Mr.Slopper}"
if [ -z "${SSLVPN_PASS:-}" ]; then
    SSLVPN_PASS="$(dd if=/dev/urandom bs=32 count=1 2>/dev/null | base64 | tr -dc 'A-Za-z0-9' | head -c 16)"
    echo "[entrypoint] generated random SSLVPN_PASS for this container start"
fi
export SSLVPN_USER SSLVPN_PASS
export LD_LIBRARY_PATH=/opt/lib
set +e
while true; do
    /app/fw_ctf_host
    echo "restarting..." >&2
    sleep 0.3
done
