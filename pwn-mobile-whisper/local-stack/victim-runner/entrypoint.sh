#!/usr/bin/env bash
set -euo pipefail

ANDROID_HOME="${ANDROID_HOME:-/opt/android-sdk}"
ADB="${ANDROID_HOME}/platform-tools/adb"
EMULATOR="${ANDROID_HOME}/emulator/emulator"
AVDMANAGER="${ANDROID_HOME}/cmdline-tools/latest/bin/avdmanager"
SDKMANAGER="${ANDROID_HOME}/cmdline-tools/latest/bin/sdkmanager"

AVD_NAME="${AVD_NAME:-whisper_victim}"
SYSTEM_IMAGE="system-images;android-34;default;x86_64"
SDK_IMAGE_DIR="${ANDROID_HOME}/system-images/android-34/default/x86_64"

APK_PATH="/artifacts/whisper.apk"

BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
BACKEND_HOST="${BACKEND_HOST:-backend}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
VICTIM_HANDLE="${VICTIM_HANDLE:-victim}"
VICTIM_PHONE="${VICTIM_PHONE:-+15550000}"
VICTIM_DISPLAY="${VICTIM_DISPLAY:-Whisper Victim}"
VICTIM_PASSWORD="${WHISPER_VICTIM_PASSWORD:-v1ct1m-wh1sper-2026}"

SYSTEM_IMG_PATH="${SYSTEM_IMG_PATH:-/mnt/system.img}"

WORK_DIR="/tmp/avd_work/${AVD_NAME}"
AVD_HOME="/root/.android"

die() { echo "FATAL: $*" >&2; exit 1; }
log() { echo "[$(date '+%H:%M:%S')] $*"; }

wait_for_boot() {
    local serial="$1"
    local timeout="${2:-300}"
    local elapsed=0
    log "  Waiting for device ${serial} to come online..."
    "${ADB}" -s "$serial" wait-for-device 2>/dev/null || true
    while true; do
        local done
        done=$("${ADB}" -s "$serial" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r' || true)
        if [[ "$done" == "1" ]]; then
            log "  Boot completed (${elapsed}s)."
            return 0
        fi
        sleep 4
        elapsed=$((elapsed + 4))
        if [[ $elapsed -ge $timeout ]]; then
            die "Device did not fully boot within ${timeout}s"
        fi
        if (( elapsed % 20 == 0 )); then
            log "  Still waiting for boot... (${elapsed}s)"
        fi
    done
}

detect_serial() {
    local timeout="${1:-60}"
    local elapsed=0
    while true; do
        local s
        s=$("${ADB}" devices 2>/dev/null | grep '^emulator-' | tail -1 | awk '{print $1}' || true)
        if [[ -n "$s" ]]; then
            echo "$s"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
        if [[ $elapsed -ge $timeout ]]; then
            return 1
        fi
    done
}

current_victim_handle() {
    local f="/tmp/victim_handle"
    if [[ -f "${f}" ]]; then
        tr -d '\r\n' < "${f}"
    else
        printf '%s' "${VICTIM_HANDLE}"
    fi
}

current_victim_phone() {
    local f="/tmp/victim_phone"
    if [[ -f "${f}" ]]; then
        tr -d '\r\n' < "${f}"
    else
        printf '%s' "${VICTIM_PHONE}"
    fi
}

log "==> Whisper local victim runner starting"
log "    AVD: ${AVD_NAME}"
log "    Backend: ${BACKEND_URL}"
log "    Victim: handle=${VICTIM_HANDLE} | phone=${VICTIM_PHONE}"
log "    system.img: ${SYSTEM_IMG_PATH}"

if [[ ! -e /dev/kvm ]]; then
    die "/dev/kvm not found. This container requires a KVM-capable host with --device /dev/kvm."
fi
log "  KVM present: /dev/kvm"

if [[ ! -f "${SYSTEM_IMG_PATH}" ]]; then
    die "system.img not found at ${SYSTEM_IMG_PATH}. Mount the player system.img at that path."
fi
log "  system.img found: $(du -h "${SYSTEM_IMG_PATH}" | cut -f1)"

log ""
log "--- Step a: Preparing work directory with player system.img ---"

mkdir -p "${WORK_DIR}"

log "  Syncing SDK image dir to ${WORK_DIR} (hard links for non-system files)..."
rsync -a --delete \
    --exclude "system.img" \
    "${SDK_IMAGE_DIR}/" "${WORK_DIR}/"

cp "${SYSTEM_IMG_PATH}" "${WORK_DIR}/system.img"

log ""
log "--- Step b: Creating AVD and booting emulator ---"

"${ADB}" devices 2>/dev/null | grep '^emulator-' | awk '{print $1}' | while read -r s; do
    avd=$("${ADB}" -s "$s" emu avd name 2>/dev/null | head -1 | tr -d '\r' || true)
    if [[ "$avd" == "${AVD_NAME}" ]]; then
        log "  Killing existing emulator ${s}..."
        "${ADB}" -s "$s" emu kill 2>/dev/null || true
        sleep 3
    fi
done || true

"${AVDMANAGER}" delete avd --name "${AVD_NAME}" 2>/dev/null || true

"${AVDMANAGER}" create avd \
    --name "${AVD_NAME}" \
    --package "${SYSTEM_IMAGE}" \
    --device "pixel_4" \
    --force

log "  AVD '${AVD_NAME}' created."

AVD_DIR="${AVD_HOME}/avd/${AVD_NAME}.avd"
if [[ -d "${AVD_DIR}" ]]; then
    for f in \
        "${AVD_DIR}/system.img.qcow2" \
        "${AVD_DIR}/vendor.img.qcow2" \
        "${AVD_DIR}/cache.img.qcow2" \
        "${AVD_DIR}/encryptionkey.img.qcow2" \
        "${AVD_DIR}/userdata-qemu.img" \
        "${AVD_DIR}/userdata-qemu.img.qcow2"; do
        [[ -f "$f" ]] && { log "  Removing stale overlay: $(basename "$f")"; rm -f "$f"; }
    done
    find "${AVD_DIR}" -name "*.lock" -delete 2>/dev/null || true
fi

log "  Launching emulator (headless, KVM, swiftshader)..."
"${EMULATOR}" \
    -avd "${AVD_NAME}" \
    -sysdir "${WORK_DIR}" \
    -no-window \
    -no-audio \
    -no-snapshot \
    -no-boot-anim \
    -gpu swiftshader_indirect \
    -writable-system \
    -wipe-data \
    -no-metrics \
    2>/tmp/emulator.log &
EMULATOR_PID=$!
log "  Emulator PID: ${EMULATOR_PID}"
echo "${EMULATOR_PID}" > /tmp/emulator.pid

log "  Detecting emulator adb serial..."
ADB_SERIAL=$(detect_serial 90) || die "Emulator did not appear in adb devices within 90s"
log "  adb serial: ${ADB_SERIAL}"
echo "${ADB_SERIAL}" > /tmp/emulator_serial

log ""
log "--- Step c: First boot + disable-verity ---"

wait_for_boot "${ADB_SERIAL}" 300
sleep 3

log "  adb root..."
"${ADB}" -s "${ADB_SERIAL}" root
sleep 3
"${ADB}" -s "${ADB_SERIAL}" wait-for-device 2>/dev/null || true

log "  adb disable-verity..."
"${ADB}" -s "${ADB_SERIAL}" disable-verity 2>&1 || true
sleep 2

log "  adb reboot..."
"${ADB}" -s "${ADB_SERIAL}" reboot
sleep 5

log "  Waiting for second boot ..."
wait_for_boot "${ADB_SERIAL}" 300
sleep 3

log "  adb root (second boot)..."
"${ADB}" -s "${ADB_SERIAL}" root
sleep 3
"${ADB}" -s "${ADB_SERIAL}" wait-for-device 2>/dev/null || true

log "  setenforce 0..."
"${ADB}" -s "${ADB_SERIAL}" shell setenforce 0 || true
SE_MODE=$("${ADB}" -s "${ADB_SERIAL}" shell getenforce 2>/dev/null | tr -d '\r' || echo "unknown")
log "  getenforce = ${SE_MODE}"

FLAG_STAT=$("${ADB}" -s "${ADB_SERIAL}" shell "ls -la /flag.txt 2>&1" | tr -d '\r')
log "  /flag.txt: ${FLAG_STAT}"
if echo "${FLAG_STAT}" | grep -qE "(No such file|not found)"; then
    die "/flag.txt not found after disable-verity+reboot. Check that system.img was baked correctly."
fi

log ""
log "--- Step d: Starting socat bridge ---"

socat TCP-LISTEN:8000,bind=127.0.0.1,fork,reuseaddr \
    "TCP:${BACKEND_HOST}:${BACKEND_PORT}" &
SOCAT_PID=$!
echo "${SOCAT_PID}" > /tmp/socat.pid
log "  socat PID: ${SOCAT_PID} (127.0.0.1:8000 -> ${BACKEND_HOST}:${BACKEND_PORT})"

log "  Waiting for backend (up to 60s)..."
for i in $(seq 1 30); do
    if curl -sf --max-time 3 "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
        log "  Backend reachable."
        break
    fi
    sleep 2
    if [[ $i -eq 30 ]]; then
        log "  WARNING: backend not reachable after 60s; continuing anyway."
    fi
done

log ""
log "--- Step e: Provisioning victim ---"

log "  Starting device service..."
"${ADB}" -s "${ADB_SERIAL}" shell "mkdir -p /dev/socket && chmod 0755 /dev/socket" 2>/dev/null || true
"${ADB}" -s "${ADB_SERIAL}" shell "pkill -x whisperd 2>/dev/null; true" || true
sleep 1
"${ADB}" -s "${ADB_SERIAL}" shell \
    "( setsid /system/bin/whisperd >/data/local/tmp/whisperd.log 2>&1 </dev/null & ) ; sleep 1" || true
sleep 2
log "  Service started."

log "  Installing APK..."
"${ADB}" -s "${ADB_SERIAL}" install -r -g "${APK_PATH}"
log "  APK installed."

APP_UID=$("${ADB}" -s "${ADB_SERIAL}" shell "pm list packages -U 2>/dev/null" \
    | grep "com.whisper.app" \
    | grep -oE "uid:[0-9]+" \
    | head -1 \
    | sed 's/uid://' \
    | tr -d '\r' || true)

if [[ -z "${APP_UID}" ]]; then
    log "  WARNING: could not read app uid; using fallback 10110."
    APP_UID="10110"
fi
log "  com.whisper.app uid = ${APP_UID}"

"${ADB}" -s "${ADB_SERIAL}" shell "mkdir -p /data/system"
"${ADB}" -s "${ADB_SERIAL}" shell "printf '%s\n' '${APP_UID}' > /data/system/whisper_app_uid"
"${ADB}" -s "${ADB_SERIAL}" shell "chmod 0644 /data/system/whisper_app_uid"

"${ADB}" -s "${ADB_SERIAL}" shell "pkill -x whisperd 2>/dev/null; true" || true
sleep 1
"${ADB}" -s "${ADB_SERIAL}" shell \
    "( WHISPERD_APP_UID=${APP_UID} setsid /system/bin/whisperd \
       >/data/local/tmp/whisperd.log 2>&1 </dev/null & ) ; sleep 1" || true
sleep 2
SERVICE_PID=$("${ADB}" -s "${ADB_SERIAL}" shell \
    "pgrep -x whisperd 2>/dev/null | head -1" | tr -d '\r' || true)
log "  Service ready (PID=${SERVICE_PID:-unknown})."

"${ADB}" -s "${ADB_SERIAL}" shell \
    "mkdir -p /data/ota_package; \
     ( setsid /system/bin/whisper_backupd >/data/local/tmp/whisper_backupd.log 2>&1 </dev/null & ); \
     ( setsid /system/bin/whisper_otad     >/data/local/tmp/whisper_otad.log     2>&1 </dev/null & ); \
     sleep 1" || true

VICTIM_TOKEN=""
if curl -sf --max-time 5 "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    REGISTER_RESPONSE=$(curl -sf \
        --max-time 10 \
        -X POST \
        -H "Content-Type: application/json" \
        -d "{\"phone\":\"${VICTIM_PHONE}\",\"handle\":\"${VICTIM_HANDLE}\",\"display_name\":\"${VICTIM_DISPLAY}\",\"password\":\"${VICTIM_PASSWORD}\",\"is_victim\":true}" \
        "http://127.0.0.1:8000/auth/register" 2>&1 || true)

    VICTIM_TOKEN=$(echo "${REGISTER_RESPONSE}" | \
        python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('token',''))" \
        2>/dev/null || true)

    if [[ -n "${VICTIM_TOKEN}" ]]; then
        log "  Victim registered: handle=${VICTIM_HANDLE}"
    else
        log "  WARNING: victim registration returned no token."
    fi
else
    log "  WARNING: backend not reachable; skipping victim registration."
fi

if [[ -n "${VICTIM_TOKEN}" ]]; then
    "${ADB}" -s "${ADB_SERIAL}" shell \
        "am start \
         -n com.whisper.app/.MainActivity \
         -a android.intent.action.MAIN \
         --es provision_token '${VICTIM_TOKEN}' \
         --es provision_backend 'http://10.0.2.2:8000' \
         --es provision_handle '${VICTIM_HANDLE}'" \
        2>/dev/null || true
    sleep 4

    log "  Waiting for the app to connect to the backend (WebSocket)..."
    ws_ok=0
    for i in $(seq 1 20); do
        if "${ADB}" -s "${ADB_SERIAL}" shell "logcat -d 2>/dev/null | grep -m1 'WebSocket opened'" \
                2>/dev/null | grep -q 'WebSocket opened'; then
            ws_ok=1
            break
        fi
        if [[ $i -eq 7 || $i -eq 14 ]]; then
            "${ADB}" -s "${ADB_SERIAL}" shell \
                "am start -n com.whisper.app/.MainActivity -a android.intent.action.MAIN \
                 --es provision_token '${VICTIM_TOKEN}' \
                 --es provision_backend 'http://10.0.2.2:8000' \
                 --es provision_handle '${VICTIM_HANDLE}'" \
                2>/dev/null || true
        fi
        sleep 4
    done
    if [[ "${ws_ok}" -eq 1 ]]; then
        log "  App connected to the backend (WebSocket opened)."
    else
        die "App never opened a WebSocket to the backend after provisioning (emulator network likely degraded). Exiting so Docker restarts with a fresh emulator."
    fi
else
    log "  Skipping app provisioning (no token)."
fi

echo "${APP_UID}"      > /tmp/app_uid
echo "${ADB_SERIAL}"   > /tmp/emulator_serial
echo "${VICTIM_HANDLE}" > /tmp/victim_handle
echo "${VICTIM_PHONE}"  > /tmp/victim_phone
touch /tmp/provisioning_done

log ""
log "================================================================"
log "READY"
log "  AVD name:   ${AVD_NAME}"
log "  adb serial: ${ADB_SERIAL}"
log "  app uid:    ${APP_UID}"
log "  getenforce: ${SE_MODE}"
log "  /flag.txt:  ${FLAG_STAT}"
log "  victim:     handle=${VICTIM_HANDLE} phone=${VICTIM_PHONE}"
log "  backend:    ${BACKEND_URL}"
log "================================================================"

log ""
log "--- Step f: Starting control API and watchdog ---"

python3 /runner_api.py &
API_PID=$!
echo "${API_PID}" > /tmp/api.pid
log "  runner_api.py PID: ${API_PID}"

_WATCHDOG_HEALED=0

while true; do
    if ! kill -0 "${EMULATOR_PID}" 2>/dev/null; then
        log "ERROR: Emulator process died. Exiting so docker can restart."
        exit 1
    fi
    if ! kill -0 "${API_PID}" 2>/dev/null; then
        log "ERROR: runner_api.py died. Exiting so docker can restart."
        exit 1
    fi

    if [[ -f /tmp/provisioning_done ]]; then
        if [[ "${_WATCHDOG_HEALED}" -eq 1 ]]; then
            _WATCHDOG_HEALED=0
        else
            APP_ALIVE=$("${ADB}" -s "${ADB_SERIAL}" \
                shell "ps -A -o NAME 2>/dev/null | grep -qx com.whisper.app && echo yes || echo no" \
                2>/dev/null | tr -d '\r' || echo "no")
            if [[ "${APP_ALIVE}" != "yes" ]]; then
                log "[watchdog] app process gone -> calling internal /reset"
                if curl -s -m 40 -X POST "http://127.0.0.1:9090/reset" >/dev/null 2>&1; then
                    log "[watchdog] victim auto-recovered"
                else
                    log "[watchdog] WARNING: /reset call failed; will retry next cycle"
                fi
                _WATCHDOG_HEALED=1
                sleep 5
                continue
            fi
        fi
    fi

    sleep 4
done
