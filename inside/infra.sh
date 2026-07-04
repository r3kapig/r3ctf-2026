#!/bin/sh
# Build + run inside. Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
set -e
NAME="inside"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"
HOST_PORT="9999"
CONTAINER_PORT="9999"
docker build . -t "$IMAGE"
docker run --rm -d --cpus "1.0" --memory "1g" \
  -e FLAG='r3ctf{infra_test_flag}' \
  -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"
