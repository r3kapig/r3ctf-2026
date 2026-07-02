#!/bin/sh
# Build + run z3kapig. Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
set -e
NAME="z3kapig"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"
HOST_PORT="1338"
CONTAINER_PORT="1337"
docker build . -t "$IMAGE"
docker run --rm -d --cpus "2.0" --memory "1g" \
  -e FLAG='r3ctf{infra_test_flag}' \
  -e POW_DIFFICULTY=26 -e PROTOCOL_TIMEOUT_SECONDS=600 \
  -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"
