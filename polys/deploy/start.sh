#!/bin/bash
set -euo pipefail

printf '%s\n' "${FLAG:-}" > /flag
chown root:nogroup /flag
chmod 0440 /flag
unset FLAG

exec su ctf -s /bin/sh -c 'exec socat -T60 TCP-LISTEN:1337,bind=0.0.0.0,reuseaddr,fork EXEC:/app/polys'
