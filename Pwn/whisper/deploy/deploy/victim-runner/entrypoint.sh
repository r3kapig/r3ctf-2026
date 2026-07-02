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
WHISPERD_BIN="/artifacts/whisperd"
BAKE_SCRIPT="/artifacts/bake_image.py"

if [ -n "${WHISPER_REAL_FLAG:-}" ]; then
    FLAG_VALUE="${WHISPER_REAL_FLAG}"
else
    FLAG_VALUE="R3CTF{local_placeholder_not_the_real_one}"
fi

BACKEND_URL="${BACKEND_URL:-http://backend:8000}"
BACKEND_HOST="${BACKEND_HOST:-backend}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
INSTANCE_ID="${INSTANCE_ID:-1}"
VICTIM_HANDLE="${VICTIM_HANDLE:-victim}"
VICTIM_PHONE="${VICTIM_PHONE:-+15550000}"
VICTIM_DISPLAY="${VICTIM_DISPLAY:-Whisper Victim}"
VICTIM_PASSWORD="${WHISPER_VICTIM_PASSWORD:-v1ct1m-wh1sper-2026}"

# Lower LCD resolution to cut swiftshader software-rendering cost on the host.
# The challenge is a native heap exploit in whisperd (triggered over the network),
# so the on-screen UI resolution is irrelevant to solvability.
AVD_LCD_WIDTH="${AVD_LCD_WIDTH:-480}"
AVD_LCD_HEIGHT="${AVD_LCD_HEIGHT:-800}"
AVD_LCD_DENSITY="${AVD_LCD_DENSITY:-160}"

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

current_victim_password() {
    local f="/tmp/victim_password"
    if [[ -f "${f}" ]]; then
        tr -d '\r\n' < "${f}"
    else
        printf '%s' "${VICTIM_PASSWORD}"
    fi
}

self_heal() {
    local serial="$1"
    local app_uid="$2"
    log "[watchdog] App process absent -- starting self-heal."

    local cur_handle cur_phone cur_password
    cur_handle=$(current_victim_handle)
    cur_phone=$(current_victim_phone)
    cur_password=$(current_victim_password)

    "${ADB}" -s "${serial}" shell "pkill -x whisperd 2>/dev/null; true" 2>/dev/null || true
    sleep 1
    "${ADB}" -s "${serial}" shell \
        "( WHISPERD_APP_UID=${app_uid} setsid /system/bin/whisperd \
           >/data/local/tmp/whisperd.log 2>&1 </dev/null & ) ; sleep 1" \
        2>/dev/null || true
    sleep 1
    local wpid
    wpid=$("${ADB}" -s "${serial}" shell "pgrep -x whisperd 2>/dev/null | head -1" \
        | tr -d '\r' || true)
    log "[watchdog] whisperd PID after restart: ${wpid:-unknown}"

    local token=""
    if curl -sf --max-time 3 "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
        local resp
        resp=$(curl -sf --max-time 8 \
            -X POST \
            -H "Content-Type: application/json" \
            -d "{\"phone\":\"${cur_phone}\",\"handle\":\"${cur_handle}\",\"display_name\":\"${VICTIM_DISPLAY}\",\"password\":\"${cur_password}\",\"is_victim\":true}" \
            "http://127.0.0.1:8000/auth/register" 2>/dev/null || true)
        token=$(echo "${resp}" | \
            python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('token',''))" \
            2>/dev/null || true)
        if [[ -n "${token}" ]]; then
            log "[watchdog] Victim re-registered (handle=${cur_handle})."
        else
            log "[watchdog] WARNING: re-registration returned no token; will restart app without login."
        fi
    else
        log "[watchdog] WARNING: backend not reachable via socat; skipping re-registration."
    fi

    "${ADB}" -s "${serial}" shell "am force-stop com.whisper.app 2>/dev/null || true" \
        2>/dev/null || true
    sleep 1
    if [[ -n "${token}" ]]; then
        "${ADB}" -s "${serial}" shell \
            "am start \
             -n com.whisper.app/.MainActivity \
             -a android.intent.action.MAIN \
             --es provision_token '${token}' \
             --es provision_backend 'http://10.0.2.2:8000' \
             --es provision_handle '${cur_handle}'" \
            2>/dev/null || true
    else
        "${ADB}" -s "${serial}" shell \
            "am start -n com.whisper.app/.MainActivity -a android.intent.action.MAIN" \
            2>/dev/null || true
    fi

    log "[watchdog] Self-heal complete (handle=${cur_handle}, token_present=${token:+yes}${token:-no}). Victim auto-recovered."
}

log "==> Whisper CTF victim-runner starting"
log "    Instance ID: ${INSTANCE_ID}"
log "    AVD: ${AVD_NAME}"
log "    Backend: ${BACKEND_URL}"
log "    Victim handle: ${VICTIM_HANDLE} | phone: ${VICTIM_PHONE}"
log "    Flag: [REDACTED (${#FLAG_VALUE} chars)]"

if [[ ! -e /dev/kvm ]]; then
    die "/dev/kvm not found. This container requires a KVM-capable host with --device /dev/kvm."
fi
log "  KVM present: /dev/kvm"

mkdir -p "${WORK_DIR}"

log "  Syncing SDK image dir to ${WORK_DIR} (hard links for non-system files)..."
rsync -a --delete \
    --exclude "system.img" \
    "${SDK_IMAGE_DIR}/" "${WORK_DIR}/"

log "  Copying system.img ($(du -h "${SDK_IMAGE_DIR}/system.img" | cut -f1)) ..."
cp "${SDK_IMAGE_DIR}/system.img" "${WORK_DIR}/system.img"

log "  Running bake_image.py (injects /flag.txt + /system/bin/whisperd) ..."
python3 "${BAKE_SCRIPT}" \
    --image    "${WORK_DIR}/system.img" \
    --flag     "${FLAG_VALUE}" \
    --whisperd "${WHISPERD_BIN}"

log "  system.img baked: /flag.txt and /system/bin/whisperd injected."

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

# Drop the pixel_4 display (1080x2280) to a small panel so swiftshader has far
# fewer pixels to rasterize per frame (biggest host-CPU drain at idle).
AVD_CFG="${AVD_HOME}/avd/${AVD_NAME}.avd/config.ini"
if [[ -f "${AVD_CFG}" ]]; then
    sed -i '/^hw\.lcd\./d' "${AVD_CFG}"
    {
        echo "hw.lcd.width = ${AVD_LCD_WIDTH}"
        echo "hw.lcd.height = ${AVD_LCD_HEIGHT}"
        echo "hw.lcd.density = ${AVD_LCD_DENSITY}"
    } >> "${AVD_CFG}"
    log "  LCD set to ${AVD_LCD_WIDTH}x${AVD_LCD_HEIGHT}@${AVD_LCD_DENSITY}dpi (was pixel_4 1080x2280)."
fi

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

wait_for_boot "${ADB_SERIAL}" 300
sleep 3

log "  adb root..."
"${ADB}" -s "${ADB_SERIAL}" root
sleep 3
"${ADB}" -s "${ADB_SERIAL}" wait-for-device 2>/dev/null || true

log "  adb disable-verity..."
"${ADB}" -s "${ADB_SERIAL}" disable-verity 2>&1 || true
sleep 2

log "  adb reboot (to apply disable-verity)..."
"${ADB}" -s "${ADB_SERIAL}" reboot
sleep 5

log "  Waiting for second boot (post disable-verity)..."
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
    die "/flag.txt not found after disable-verity+reboot. bake_flag.py or verity step failed."
fi

UNPRIV=$("${ADB}" -s "${ADB_SERIAL}" shell "su 2000 sh -c 'cat /flag.txt 2>&1'" | tr -d '\r' || true)
if echo "${UNPRIV}" | grep -qiE "^R3CTF\{"; then
    log "  WARNING: non-root can read /flag.txt -- check permissions" >&2
else
    log "  Non-root access blocked (expected 'Permission denied'). OK."
fi

log "--- Step d: Starting socat bridge 127.0.0.1:8000 -> ${BACKEND_HOST}:${BACKEND_PORT} ---"
socat TCP-LISTEN:8000,bind=127.0.0.1,fork,reuseaddr \
    "TCP:${BACKEND_HOST}:${BACKEND_PORT}" &
SOCAT_PID=$!
echo "${SOCAT_PID}" > /tmp/socat.pid
log "  socat PID: ${SOCAT_PID} (127.0.0.1:8000 -> ${BACKEND_HOST}:${BACKEND_PORT})"

log "  Waiting for backend health (up to 60s)..."
for i in $(seq 1 30); do
    if curl -sf --max-time 3 "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
        log "  Backend reachable via socat."
        break
    fi
    sleep 2
    if [[ $i -eq 30 ]]; then
        log "  WARNING: backend not reachable after 60s; continuing anyway (provision step will retry)."
    fi
done

log "--- Step d.5: Applying egress firewall ---"

apply_egress_firewall() {
    local backend_host="${BACKEND_HOST:-backend}"
    local backend_port="${BACKEND_PORT:-8000}"

    if ! command -v iptables >/dev/null 2>&1; then
        echo "FATAL [firewall]: iptables not installed -- egress firewall NOT applied." >&2
        return 1
    fi

    local backend_ips
    backend_ips=$(getent hosts "${backend_host}" 2>/dev/null | awk '{print $1}' | sort -u)

    if [[ -z "${backend_ips}" ]]; then
        local retries=5
        while [[ $retries -gt 0 ]]; do
            sleep 2
            backend_ips=$(getent hosts "${backend_host}" 2>/dev/null | awk '{print $1}' | sort -u)
            [[ -n "${backend_ips}" ]] && break
            retries=$((retries - 1))
        done
    fi

    if [[ -z "${backend_ips}" ]]; then
        echo "FATAL [firewall]: could not resolve ${backend_host} -- egress firewall NOT applied." >&2
        return 1
    fi

    log "  [firewall] Resolved ${backend_host} -> $(echo "${backend_ips}" | tr '\n' ' ')"

    iptables -N WHISPER_EGRESS 2>/dev/null || iptables -F WHISPER_EGRESS

    if ! iptables -C OUTPUT -j WHISPER_EGRESS 2>/dev/null; then
        iptables -I OUTPUT -j WHISPER_EGRESS
    fi

    iptables -A WHISPER_EGRESS -o lo -j ACCEPT
    iptables -A WHISPER_EGRESS -m state --state ESTABLISHED,RELATED -j ACCEPT

    iptables -A WHISPER_EGRESS -d 127.0.0.11 -p udp --dport 53 -j ACCEPT
    iptables -A WHISPER_EGRESS -d 127.0.0.11 -p tcp --dport 53 -j ACCEPT

    local ip
    while IFS= read -r ip; do
        [[ -z "${ip}" ]] && continue
        iptables -A WHISPER_EGRESS -d "${ip}" -p tcp --dport "${backend_port}" -j ACCEPT
        log "  [firewall] ALLOW tcp -> ${ip}:${backend_port} (backend)"
    done <<< "${backend_ips}"

    iptables -A WHISPER_EGRESS -m limit --limit 5/min --limit-burst 10 \
        -j LOG --log-prefix "[WHISPER_DROP] " --log-level 4
    iptables -A WHISPER_EGRESS -j DROP

    if ! iptables -C OUTPUT -j WHISPER_EGRESS 2>/dev/null \
       || ! iptables -C WHISPER_EGRESS -j DROP 2>/dev/null; then
        echo "FATAL [firewall]: egress rules did not apply (chain/jump missing)." >&2
        return 1
    fi

    log "  [firewall] Egress firewall applied: loopback+established+DNS+backend ALLOWED; all other outbound DROPPED."
    return 0
}

if ! apply_egress_firewall; then
    echo "FATAL: egress firewall could not be applied. Aborting to prevent uncontrolled internet access." >&2
    exit 1
fi

log "  Starting whisperd from /system/bin/whisperd (baked into image)..."
"${ADB}" -s "${ADB_SERIAL}" shell "mkdir -p /dev/socket && chmod 0755 /dev/socket" 2>/dev/null || true
"${ADB}" -s "${ADB_SERIAL}" shell "pkill -x whisperd 2>/dev/null; true" || true
sleep 1
"${ADB}" -s "${ADB_SERIAL}" shell \
    "( setsid /system/bin/whisperd >/data/local/tmp/whisperd.log 2>&1 </dev/null & ) ; sleep 1" || true
sleep 2
log "  whisperd started (pre-APK install, uid fallback active)."

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
    log "  WARNING: could not read app uid from pm; using fallback 10110."
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
WHISPERD_PID=$("${ADB}" -s "${ADB_SERIAL}" shell \
    "pgrep -x whisperd 2>/dev/null | head -1" | tr -d '\r' || true)
log "  whisperd restarted with WHISPERD_APP_UID=${APP_UID}, PID=${WHISPERD_PID:-unknown}"

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
        log "  Victim registered: handle=${VICTIM_HANDLE}, token=[${#VICTIM_TOKEN} chars]"
    else
        log "  WARNING: victim registration did not return a token. Response: ${REGISTER_RESPONSE:-<empty>}"
    fi
else
    log "  WARNING: backend not reachable via socat; skipping victim registration."
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
    log "  Skipping app provisioning intent (no token)."
fi

echo "${APP_UID}" > /tmp/app_uid
echo "${ADB_SERIAL}" > /tmp/emulator_serial
echo "${INSTANCE_ID}" > /tmp/instance_id
echo "${VICTIM_HANDLE}" > /tmp/victim_handle
echo "${VICTIM_PHONE}"  > /tmp/victim_phone
touch /tmp/provisioning_done

log ""
log "================================================================"
log "READY"
log "  Instance:   ${INSTANCE_ID}"
log "  AVD name:   ${AVD_NAME}"
log "  adb serial: ${ADB_SERIAL}"
log "  app uid:    ${APP_UID}"
log "  getenforce: ${SE_MODE}"
log "  /flag.txt:  ${FLAG_STAT}"
log "  victim:     handle=${VICTIM_HANDLE} phone=${VICTIM_PHONE}"
log "  backend:    ${BACKEND_URL} (socat 127.0.0.1:8000 -> ${BACKEND_HOST}:${BACKEND_PORT})"
log "  whisperd:   /system/bin/whisperd (baked into image)"
log "  watchdog:   self-healing enabled (app process check every ~4s)"
log "================================================================"

python3 /runner_api.py &
API_PID=$!
echo "${API_PID}" > /tmp/api.pid
log "  runner_api.py PID: ${API_PID}"

_WATCHDOG_HEALED=0

while true; do
    if ! kill -0 "${EMULATOR_PID}" 2>/dev/null; then
        log "ERROR: Emulator process (PID ${EMULATOR_PID}) died. Exiting so docker can restart."
        exit 1
    fi
    if ! kill -0 "${API_PID}" 2>/dev/null; then
        log "ERROR: runner_api.py (PID ${API_PID}) died. Exiting so docker can restart."
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
                log "[watchdog] app process absent -> calling internal /reset"
                if curl -s -m 40 -X POST "http://127.0.0.1:${RUNNER_PORT:-9090}/reset" >/dev/null 2>&1; then
                    log "[watchdog] victim auto-recovered via /reset"
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
