#!/bin/sh
# Dynamic flag entrypoint for the Mafuyuuuuu backend.
# The platform injects the per-team flag via $FLAG (also $GZCTF_FLAG / $DASFLAG).
# Write it to /flag (the backend reads it through the setuid /readflag binary),
# scrub the env, then start supervisord (which runs the backend as appuser).
set -eu

if [ -n "${DASFLAG:-}" ]; then
    INSERT_FLAG="$DASFLAG"
elif [ -n "${FLAG:-}" ]; then
    INSERT_FLAG="$FLAG"
elif [ -n "${GZCTF_FLAG:-}" ]; then
    INSERT_FLAG="$GZCTF_FLAG"
else
    INSERT_FLAG="r3ctf{test_flag_replace_me}"
fi

printf '%s\n' "$INSERT_FLAG" > /flag
chown root:root /flag
chmod 400 /flag

# Scrub the flag from the environment so the backend process never sees it.
DASFLAG=no_FLAG
FLAG=no_FLAG
GZCTF_FLAG=no_FLAG
export DASFLAG FLAG GZCTF_FLAG

exec /usr/bin/supervisord -c /etc/supervisor/conf.d/papertrail.conf
