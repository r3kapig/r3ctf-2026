#!/bin/sh
# entrypoint.sh -- R3CTF dynamic-flag entrypoint for Blinky.
#
# The image bakes only a PLACEHOLDER flag. At container start we bake the real
# $FLAG (injected by the platform) into the kernel image, then scrub it from the
# environment so the running server process cannot leak it. The PAC key is NOT set
# here -- server.py randomises it per submission.
set -eu

APP="${APP:-/app/server}"

# Smoke-test the prebuilt simulator: if the base image's glibc/libstdc++ is too old
# for SOC_run_sim it silently fails to exec and every submission returns
# "(no output)". Catch that here with a clear message instead.
if ldd "$APP/SOC_run_sim" 2>&1 | grep -q "not found"; then
    echo "[entrypoint] FATAL: SOC_run_sim has unmet shared-library deps:" >&2
    ldd "$APP/SOC_run_sim" 2>&1 | grep "not found" >&2
    echo "[entrypoint] the base image is too old for this prebuilt binary "\
         "(need a newer glibc/libstdc++); bump the Dockerfile base image." >&2
    exit 1
fi

# Do NOT write `${FLAG:=r3ctf{...}}` -- a '}' inside a shell brace-default closes
# the expansion early. Use a plain empty-check instead.
if [ -z "${FLAG:-}" ]; then
    FLAG='R3CTF{TEST_Dynamic_FLAG}'
fi

echo "[entrypoint] baking flag into kernel image ..."
FLAG="$FLAG" OUT="$APP/kernel_template.mem" "$APP/build_kernel.sh"

# Scrub the flag from the environment (R3CTF convention) before exec'ing the
# server. server.py never reads $FLAG (the flag now lives only in the baked image).
FLAG=no_FLAG
export FLAG
unset FLAG

echo "[entrypoint] starting server on ${HOST:-0.0.0.0}:${PORT:-8080}"
exec python3 "$APP/server.py"
