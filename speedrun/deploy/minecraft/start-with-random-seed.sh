#!/bin/bash
set -euo pipefail

level_name="${LEVEL:-world}"
seed="${SEED:-}"

if [[ "${RANDOMIZE_SEED_ON_START:-true}" == "true" || -z "${seed}" ]]; then
  seed="$(date +%s%N)"
  export SEED="${seed}"
fi

if [[ "${RESET_WORLD_ON_START:-true}" == "true" ]]; then
  rm -rf \
    "/data/${level_name}" \
    "/data/${level_name}_nether" \
    "/data/${level_name}_the_end"
fi

echo "[speedrun] Starting with seed: ${SEED}"
exec /start
