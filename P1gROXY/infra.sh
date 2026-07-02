#!/bin/sh
# Build + run the challenge. Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
set -e
NAME="p1groxy"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
HOST_PORT="30003"
CONTAINER_PORT="8080"
IMAGE="$REG/$NAME:$TAG"
docker build . -t "$IMAGE"
docker run --rm -d -e FLAG='r3ctf{infra_test_flag}' --cpus "0.1" --memory "128m" -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"
