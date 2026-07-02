#!/bin/sh
# Build + run rECp1cG. Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
set -e
NAME="recp1cg"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"
HOST_PORT="30005"
CONTAINER_PORT="9999"

docker build . -t "$IMAGE"
docker run --rm -d -e FLAG='r3ctf{infra_test_flag}' \
  --cpus "0.1" --memory "128m" \
  -p "$HOST_PORT:$CONTAINER_PORT" \
  "$IMAGE"
