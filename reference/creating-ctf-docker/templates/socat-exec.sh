#!/bin/sh
# socat EXEC forwarder — spawns the challenge once per TCP connection.
# Pick the variant that matches your app. Drop the leading comment to use.

# Python REPL-style session (crypto no_socket / pyjail):
exec socat TCP4-LISTEN:9999,tcpwrap=script,reuseaddr,fork \
     EXEC:"python3 -u /app/main.py",stderr

# SageMath session:
# exec socat TCP4-LISTEN:9999,tcpwrap=script,reuseaddr,fork \
#      EXEC:"sage /home/sage/main.sage"

# Compiled binary, drop to user ctf, idle timeout 600s, raw pty:
# exec socat -T600 TCP-LISTEN:5000,reuseaddr,fork,su=ctf \
#      EXEC:/app/main,pty,echo=0,rawer

# Drop privileges via su wrapper (socat runs as root), with per-conn timeout:
# exec socat tcp-listen:1337,fork,reuseaddr,bind=0.0.0.0 \
#      exec:"su ctf -c 'timeout 60 /pwn'",stderr
