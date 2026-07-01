# victim-runner

Self-contained Docker image that boots a goldfish Android 14 (API 34) AVD
inside a KVM-privileged container, provisions the Whisper CTF challenge, and
exposes a control API on port 9090 for the judge worker.

The victim is **self-healing**: if the app process exits, the supervisor loop
inside the container automatically re-provisions it within ~10 seconds -- no
external `/reset` call needed.

## Network path

The Android emulator maps `10.0.2.2` to the container's own loopback.
The Whisper app is provisioned with `provision_backend=http://10.0.2.2:8000`.
Inside the container, `socat` listens on `127.0.0.1:8000` and forwards to
the `backend` container:

```
  [emulator] http://10.0.2.2:8000
        |
        v (emulator NAT: 10.0.2.2 -> 127.0.0.1)
  [container loopback] 127.0.0.1:8000
        |
        v  socat TCP-LISTEN:8000,bind=127.0.0.1,fork,reuseaddr TCP:backend:8000
  [backend container] backend:8000
```

## Boot sequence (entrypoint.sh)

1. KVM check: exit 1 if `/dev/kvm` absent.
2. **Flag bake**: copies `system.img` from the SDK image dir into `/tmp/avd_work/`,
   runs `bake_image.py --image ... --flag $WHISPER_REAL_FLAG` to inject `/flag.txt`
   (mode 0600, uid/gid 0) into the ext4 before first boot.
3. **Create AVD**: `avdmanager create avd --name whisper_victim --package
   system-images;android-34;default;x86_64 --device pixel_4 --force`. Removes
   stale `.qcow2` overlays that would shadow the baked image.
4. **First boot**: `emulator -avd whisper_victim -sysdir /tmp/avd_work/whisper_victim
   -no-window -no-audio -no-snapshot -no-boot-anim -gpu swiftshader_indirect
   -writable-system -wipe-data`. Wait for `sys.boot_completed=1`.
5. **dm-verity**: `adb root` -> `adb disable-verity` -> `adb reboot`. Required
   for the baked ext4 blocks to be visible. After reboot wait for boot again.
6. **Permissive SELinux**: `adb root` -> `adb shell setenforce 0`.
7. **Verify `/flag.txt`**: confirm present and non-root access denied.
8. **socat bridge**: start forwarding loop.
9. **Provision**:
   - start `whisperd` as root
   - `adb install -r -g /artifacts/whisper.apk`
   - read app uid via `pm list packages -U | grep com.whisper.app`
   - write uid to `/data/system/whisper_app_uid`
   - restart `whisperd` with `WHISPERD_APP_UID=<uid>`
   - `curl POST /auth/register` to backend via socat -> get victim token
   - `am start -n com.whisper.app/.MainActivity ... --es provision_token ...
     --es provision_backend http://10.0.2.2:8000 --es provision_handle victim`
   - touch `/tmp/provisioning_done` (enables watchdog)
10. **Supervisor loop** (foreground):
    - `python3 /runner_api.py` starts on `0.0.0.0:9090` in background.
    - Every ~4s: checks emulator and API are alive (exits if not, so docker restarts).
    - **App-process watchdog**: if the app process is absent, triggers self-heal.

## Self-healing watchdog

When the app process exits, the watchdog automatically:

1. Restarts `whisperd` as root with the correct app uid.
2. Re-registers the victim account on the backend (idempotent in CTF mode).
3. Force-stops and relaunches the app via provisioning intent.
4. Waits 5s (debounce) before re-checking.

The watchdog and `/reset` share a flock lock (`/tmp/watchdog.lock`) to prevent
races.

Log lines:
```
[watchdog] App process absent -- starting self-heal.
[watchdog] Self-heal complete (token_present=yes). Victim auto-recovered.
```

## /reset endpoint

Port 9090 is on the **internal Docker network only** -- never published to the
host. If `RUNNER_ADMIN_TOKEN` is set, `/reset` requires:
```
Authorization: Bearer <RUNNER_ADMIN_TOKEN>
```
`GET /health` is always open.

Example (from another container on the internal network):
```bash
curl -X POST http://victim-runner:9090/reset
curl -X POST http://victim-runner:9090/reset \
  -H "Authorization: Bearer ${RUNNER_ADMIN_TOKEN}"
```

## /health response

```json
{
  "status": "ok",
  "service": "victim-runner",
  "boot": true,
  "serial": "emulator-5554",
  "app_uid": "10110",
  "flag_present": true,
  "whisperd_pid": "1234"
}
```

The judge healthcheck waits for `"boot": true` before accepting attempts.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `WHISPER_REAL_FLAG` | (placeholder) | Real flag baked into system.img. |
| `BACKEND_URL` | `http://backend:8000` | Informational; parsed into HOST+PORT. |
| `BACKEND_HOST` | `backend` | Compose service name for socat target. |
| `BACKEND_PORT` | `8000` | Backend port for socat target. |
| `VICTIM_HANDLE` | `victim` | Victim account handle. |
| `VICTIM_PHONE` | `+15550000` | Victim account phone. |
| `VICTIM_DISPLAY` | `Whisper Victim` | Victim display name. |
| `AVD_NAME` | `whisper_victim` | Android AVD name. |
| `RUNNER_HOST` | `0.0.0.0` | API bind address. |
| `RUNNER_PORT` | `9090` | API port. |
| `RUNNER_ADMIN_TOKEN` | (unset) | Bearer token required for POST /reset. |

## Build size

~3-4 GB total (Debian base, Android SDK, emulator, system image, artifacts).
Build time: 15-30 min on first run (SDK download).

## KVM host requirement

The container runs `--privileged` with `/dev/kvm` mapped. The host must have
KVM enabled. For cloud VMs, nested virtualization must be on.

Bare-metal x86_64 always works. Cloud options:
- GCP: `c2-standard-*` / `n2-standard-*` with `--enable-nested-virtualization`.
- AWS: `metal` instances.
- Azure: `Dv3`/`Ev3` with nested virt enabled.
- Hetzner: dedicated servers.

Check: `[ -e /dev/kvm ] && echo KVM_OK || echo NO_KVM`.

## Build and run

```bash
WHISPER_REAL_FLAG="R3CTF{real_flag}" \
WHISPER_ADMIN_TOKEN="changeme" \
docker compose -f deploy/docker-compose.yml up -d --build

docker compose -f deploy/docker-compose.yml logs -f victim-runner

# Health check (internal only; never published to host):
docker exec victim-runner curl -s http://127.0.0.1:9090/health

# Force reset:
docker exec victim-runner curl -s -X POST http://127.0.0.1:9090/reset

# Teardown:
docker compose -f deploy/docker-compose.yml down
```
