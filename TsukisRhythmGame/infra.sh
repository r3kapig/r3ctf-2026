#!/bin/sh
# Build + run Tsuki's Rhythm Game. Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
set -e
NAME="tsukisrhythmgame"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"
HOST_PORT="5000"
CONTAINER_PORT="5000"
docker build . -t "$IMAGE"
docker run --rm -d -e FLAG='R3CTF{infra_test_flag}' --cpus "0.1" --memory "128m" \
  -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"
