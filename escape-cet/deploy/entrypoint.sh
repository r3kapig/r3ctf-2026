#!/usr/bin/env bash
set -euo pipefail

true_flag=/root/flag

if [[ -z "${FLAG+x}" || -z "$FLAG" ]]; then
    printf 'internal error: FLAG is not set\n' >&2
    exit 1
fi

umask 077
printf '%s\n' "$FLAG" > "$true_flag"
export FLAG=
unset FLAG
chown root:root "$true_flag"
chmod 400 "$true_flag"

exec /usr/local/bin/tdocker-server
