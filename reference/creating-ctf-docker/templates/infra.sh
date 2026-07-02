#!/bin/sh
# Build + run the challenge against the contest registry.
# Run this FROM INSIDE the deploy/ directory (the Dockerfile is the build context):
#   cd deploy && ../infra.sh
set -e

NAME="mychal"                                                       # challenge / image name
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"              # contest registry namespace
TAG="latest"
HOST_PORT="30001"                              # unique host port for this challenge
CONTAINER_PORT="9999"                          # the port the service listens on inside
IMAGE="$REG/$NAME:$TAG"

docker build . -t "$IMAGE"
docker run --rm -d \
  -e FLAG='flag{infra_test_flag}' \
  --cpus "0.1" --memory "128m" \
  -p "$HOST_PORT:$CONTAINER_PORT" \
  "$IMAGE"
