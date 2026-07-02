#!/bin/sh
set -eu

rm -f /app/docker-entrypoint.sh

exec socat -v -s TCP4-LISTEN:9999,reuseaddr,fork EXEC:"/app/he_server",stderr
