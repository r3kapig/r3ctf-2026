#!/bin/sh
# Build + run r3reach. Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
set -e
NAME="r3reach"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"
HOST_PORT="25565"
CONTAINER_PORT="25565"
docker build . -t "$IMAGE"
docker run --rm -d --cpus "2.0" --memory "3g" \
  -e FLAG='r3ctf{infra_test_flag}' \
  -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"
