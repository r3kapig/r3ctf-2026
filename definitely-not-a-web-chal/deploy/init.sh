#!/bin/sh

set -eu

if [ -z "${FLAG+x}" ]; then
    echo "FLAG environment variable is required" >&2
    exit 1
fi

printf '%s' "$FLAG" > /flag
chown root:root /flag
chmod 0400 /flag
unset FLAG

service nginx start
exec env -u FLAG /app/php-bin/DEBUG/sbin/php-fpm -c /app/php-bin/DEBUG/etc/php.ini --nodaemonize
