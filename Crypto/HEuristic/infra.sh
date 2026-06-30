#!/bin/sh
# Build + run the challenge. Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
set -e
NAME="heuristic"
REG="r3ctf.ops.ret.sh.cn/r3ctf_2026"
TAG="v0"
HOST_PORT="30002"
CONTAINER_PORT="9999"
IMAGE="$REG/$NAME:$TAG"
docker build . -t "$IMAGE"
docker run --rm -d -e FLAG='flag{infra_test_flag}' --cpus "0.1" --memory "256m" -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"
