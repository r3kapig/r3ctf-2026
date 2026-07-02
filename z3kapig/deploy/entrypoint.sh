#!/bin/sh
set -eu

# Dynamic flag: the platform injects the per-team flag via $FLAG; write it to
# flag.txt (root-only) and scrub the env. Falls back to a placeholder for local
# runs. The entrypoint runs as the ctf user which owns flag.txt.
FLAG_FILE=/home/ctf/app/flag.txt
INSERT_FLAG="${FLAG:-r3ctf{TEST_Dynamic_FLAG}}"
export FLAG=no_FLAG
FLAG=no_FLAG
chmod 0600 "$FLAG_FILE" 2>/dev/null || true
printf '%s' "$INSERT_FLAG" > "$FLAG_FILE"
chmod 0400 "$FLAG_FILE"

exec "$@"
