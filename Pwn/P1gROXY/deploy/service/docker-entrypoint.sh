#!/bin/sh
# Resolve + scrub the platform flag, deliver it to /flag.txt, then drop
# privileges and start the proxy + warehousehub stack.
if [ -n "$FLAG" ]; then
    INSERT_FLAG="$FLAG"
    export FLAG=no_FLAG
    FLAG=no_FLAG
else
    INSERT_FLAG="r3ctf{placeholder}"
fi
printf '%s\n' "$INSERT_FLAG" > /flag.txt
chown root:root /flag.txt
chmod 0444 /flag.txt
# Drop to the unprivileged service user and exec the original launcher.
exec su warehousehub -s /bin/sh -c './deploy/run-container.sh'
