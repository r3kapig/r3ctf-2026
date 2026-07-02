#!/bin/sh
# r3map: kernel pwn, one QEMU/KVM VM per connection.
# Build context is the challenge root (deploy/Dockerfile COPYs attachment/...).
# Run FROM the challenge root.
set -e
NAME="r3map"
REG="registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700"
TAG="latest"
IMAGE="$REG/$NAME:$TAG"

docker build -f deploy/Dockerfile -t "$IMAGE" .
docker run --rm -d \
  --device /dev/kvm --security-opt seccomp=unconfined \
  -e FLAG='flag{infra_test_flag}' \
  --cpus "2" --memory "3g" \
  -p 1337:1337 \
  "$IMAGE"
