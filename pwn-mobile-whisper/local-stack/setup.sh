#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"

APK_SRC="${DIST_DIR}/whisper.apk"
IMG_SRC="${DIST_DIR}/system.img"

APK_DST="${SCRIPT_DIR}/victim-runner/whisper.apk"
IMG_DST="${SCRIPT_DIR}/system.img"

if [[ -f "${APK_SRC}" ]] && [[ ! -f "${APK_DST}" ]]; then
    cp "${APK_SRC}" "${APK_DST}"
    echo "Copied whisper.apk -> victim-runner/whisper.apk"
fi

if [[ -f "${IMG_SRC}" ]] && [[ ! -f "${IMG_DST}" ]]; then
    cp "${IMG_SRC}" "${IMG_DST}"
    echo "Copied system.img -> local-stack/system.img"
fi

if [[ ! -f "${APK_DST}" ]]; then
    echo "ERROR: whisper.apk not found. Place it at ${APK_DST}" >&2
    exit 1
fi

if [[ ! -f "${IMG_DST}" ]]; then
    echo "ERROR: system.img not found. Place it at ${IMG_DST}" >&2
    exit 1
fi

echo "Setup complete. Run: cd dist/local-stack && docker compose up"
