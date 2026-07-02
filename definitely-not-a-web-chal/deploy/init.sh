#!/bin/sh

service nginx start
exec /app/php-bin/DEBUG/sbin/php-fpm -c /app/php-bin/DEBUG/etc/php.ini --nodaemonize