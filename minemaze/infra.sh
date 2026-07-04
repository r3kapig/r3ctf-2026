#!/bin/sh
# minemaze: Minecraft Folia "blind maze" challenge (RekaMaze plugin).
# The image is pre-built (see deploy/docker-compose.yml) and pushed to the
# registry; this script just runs a local instance for testing.
# Run FROM the challenge root.
set -e
NAME="minemaze"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"

docker pull "$IMAGE"
docker run --rm -d --name "$NAME" \
  -e FLAG='r3ctf{infra_test_flag}' \
  -e INIT_MEMORY='1G' -e MAX_MEMORY='3G' \
  --cpus "2" --memory "4g" \
  -p 25565:25565 \
  "$IMAGE"
echo "minemaze listening on :25565 (connect with a vanilla Minecraft 1.21.x client)"
