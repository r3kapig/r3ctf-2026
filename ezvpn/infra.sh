#!/bin/sh
# Build + run ezvpn. Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
set -e
NAME="ezvpn"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"
HOST_PORT="30004"
CONTAINER_PORT="4433"
docker build . -t "$IMAGE"
docker run --rm -d -e FLAG='flag{infra_test_flag}' --cpus "0.1" --memory "128m" \
  -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"
