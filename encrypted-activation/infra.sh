#!/bin/sh
# Encrypted Activation: FHE crypto challenge, stdin/stdout service wrapped by socat.
# Build context is the challenge root (deploy/Dockerfile COPYs attachment/...).
# Run FROM the challenge root.
set -e
NAME="encrypted-activation"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"

docker build -f deploy/Dockerfile -t "$IMAGE" .
docker run --rm -d \
  -e FLAG='r3ctf{infra_test_flag}' \
  --cpus "1" --memory "512m" \
  -p 1336:1336 \
  "$IMAGE"
