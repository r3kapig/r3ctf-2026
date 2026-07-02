#!/bin/sh
# Build + run ploys. Run FROM the ploys/ ROOT (build context is the repo root
# so the Dockerfile can reach both attachment/ploys and deploy/start.sh):
#   ./infra.sh
set -e
NAME="ploys"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"
HOST_PORT="1337"
CONTAINER_PORT="1337"
docker build -f deploy/Dockerfile -t "$IMAGE" .
docker run --rm -d --cpus "0.5" --memory "128m" \
  -e FLAG='r3ctf{infra_test_flag}' \
  -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"
