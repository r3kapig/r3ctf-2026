#!/bin/sh
# Build + run Mafuyuuuuu. Run from the challenge root:
#   ./infra.sh
set -e
cd "$(dirname "$0")/deploy"
docker compose up -d --build
