#!/bin/sh
# NOTE: multi-service; for a full local stack use:  cd deploy/docker && docker compose up -d
# Build + run the challenge. Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
set -e
NAME="fw-vpn"
REG="r3ctf.ops.ret.sh.cn/r3ctf_2026"
TAG="v0"
HOST_PORT="30001"
CONTAINER_PORT="4433"
IMAGE="$REG/$NAME:$TAG"
docker build . -t "$IMAGE"
docker run --rm -d -e FLAG='flag{infra_test_flag}' --cpus "0.1" --memory "128m" -p "$HOST_PORT:$CONTAINER_PORT" "$IMAGE"
