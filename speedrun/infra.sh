#!/bin/sh
# Build + run speedrun (minecraft + checker) locally.
# Run FROM INSIDE deploy/:  cd deploy && ../infra.sh
set -e
docker compose up --build -d
