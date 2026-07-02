#!/bin/sh
# Generic dynamic-flag entrypoint for CTF competition containers.
# The flag is supplied via the $FLAG environment variable.
# 1. Read $FLAG, then SCRUB it (overwrite with no_FLAG) so the challenge
#    process cannot leak it via `env` or /proc/<pid>/environ.
# 2. Deliver it (here: write to /flag). Adjust the delivery block to your
#    challenge (see reference/flag-injection.md).
# 3. Start the service. Put ALL cleanup (rm -f $0) BEFORE the long-running start.

set -e

# --- resolve + scrub ---
if [ -n "$FLAG" ]; then
    INSERT_FLAG="$FLAG"
    export FLAG=no_FLAG
    FLAG=no_FLAG
else
    INSERT_FLAG="flag{TEST_Dynamic_FLAG}"
fi

# --- deliver (pick ONE; default: world-readable /flag for RCE challenges) ---
echo "$INSERT_FLAG" | tee /flag
chmod 744 /flag
# For root-only/privesc:  echo -n "$INSERT_FLAG" > /root/flag_$(head -c32 /dev/urandom|tr -cd a-f0-9).txt; chmod 400 ...
# For DB (SQLi):          mysql ... -e "insert into flag values('$INSERT_FLAG');"
# For bot/XSS:            chown bot:bot /flag && chmod 400 /flag  (and do NOT put it in the app container)

# --- cleanup before start (do this BEFORE sleep infinity / exec) ---
rm -f "$0"

# --- start service (pick ONE) ---
# xinetd:    /etc/init.d/xinetd start; sleep infinity
# socat:     exec socat TCP4-LISTEN:9999,tcpwrap=script,reuseaddr,fork EXEC:"python3 -u /app/main.py",stderr
# flask:     cd /app && exec flask run -h 0.0.0.0 -p 8080
# php-fpm:   php-fpm & nginx & tail -F /var/log/nginx/*.log
# java:      exec java -jar /app/app.jar
/etc/init.d/xinetd start
sleep infinity
