#!/bin/sh
# Build + run definitely-not-a-web-chal. Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
# NOTE: builds PHP from source (heavy, ~10-20 min).
set -e
NAME="definitely-not-a-web-chal"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"
HOST_PORT="8082"
CONTAINER_PORT="80"
docker build . -t "$IMAGE"
docker run --rm -d --cpus "0.5" --memory "256m" \
  -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"
