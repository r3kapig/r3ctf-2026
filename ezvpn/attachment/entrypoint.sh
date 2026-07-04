#!/bin/sh
: "${SSLVPN_USER:=Mr.Slopper}"
: "${SSLVPN_PASS:=QWZ0M3JBVTdoWWU1}"
export SSLVPN_USER SSLVPN_PASS
export LD_LIBRARY_PATH=/opt/lib
set +e
while true; do
    /app/eazyvpn
    echo "restarting..." >&2
    sleep 0.3
done
