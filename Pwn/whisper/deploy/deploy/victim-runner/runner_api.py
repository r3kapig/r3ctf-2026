#!/usr/bin/env python3

import fcntl
import hashlib
import http.server
import json
import logging
import os
import re
import subprocess
import sys
import threading
import time
import urllib.request
import urllib.error

_FLAG_RE = re.compile(r'^r3ctf\{[^}]+\}$', re.IGNORECASE)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [runner_api] %(levelname)s %(message)s",
    stream=sys.stdout,
)
log = logging.getLogger("runner_api")

ANDROID_HOME    = os.environ.get("ANDROID_HOME", "/opt/android-sdk")
ADB             = os.path.join(ANDROID_HOME, "platform-tools", "adb")
BACKEND_HOST    = os.environ.get("BACKEND_HOST", "backend")
BACKEND_PORT    = os.environ.get("BACKEND_PORT", "8000")
BACKEND_LOCAL   = f"http://127.0.0.1:{BACKEND_PORT}"
DEVICE_BACKEND  = "http://10.0.2.2:8000"
INSTANCE_ID     = os.environ.get("INSTANCE_ID", "1")

_ENV_VICTIM_HANDLE  = os.environ.get("VICTIM_HANDLE", "victim")
_ENV_VICTIM_PHONE   = os.environ.get("VICTIM_PHONE", "+15550000")
_ENV_VICTIM_DISPLAY = os.environ.get("VICTIM_DISPLAY", "Whisper Victim")
_ENV_VICTIM_PASSWORD = os.environ.get("WHISPER_VICTIM_PASSWORD", "v1ct1m-wh1sper-2026")

WHISPER_FLAG    = os.environ.get("WHISPER_REAL_FLAG", "")
RUNNER_HOST     = os.environ.get("RUNNER_HOST", "0.0.0.0")
RUNNER_PORT     = int(os.environ.get("RUNNER_PORT", "9090"))

RUNNER_ADMIN_TOKEN = os.environ.get("RUNNER_ADMIN_TOKEN", "")

APK_PATH        = "/artifacts/whisper.apk"
WHISPERD_BIN    = "/artifacts/whisperd"

WATCHDOG_LOCK_PATH = "/tmp/watchdog.lock"
HANDLE_FILE   = "/tmp/victim_handle"
PHONE_FILE    = "/tmp/victim_phone"
PASSWORD_FILE = "/tmp/victim_password"

def _current_handle():
    return _read_file(HANDLE_FILE, _ENV_VICTIM_HANDLE)

def _current_phone():
    return _read_file(PHONE_FILE, _ENV_VICTIM_PHONE)

def _current_password():

    return _read_file(PASSWORD_FILE, _ENV_VICTIM_PASSWORD)

def _derive_phone(handle):

    digest = hashlib.sha256(handle.encode()).hexdigest()
    digits = str(int(digest[:16], 16) % 10_000_000_000).zfill(10)
    return f"+1{digits}"

def _persist_identity(handle, phone, password=None):

    _write_file(HANDLE_FILE, handle)
    _write_file(PHONE_FILE, phone)
    if password is not None:
        _write_file(PASSWORD_FILE, password)
    log.info("Persisted identity: handle=%s, phone=%s, password_set=%s",
             handle, phone, password is not None)

_reset_lock = threading.Lock()

def _read_file(path, default=""):
    try:
        with open(path) as f:
            return f.read().strip()
    except OSError:
        return default

def _write_file(path, content):
    with open(path, "w") as f:
        f.write(content)

def _adb(serial, *args, timeout=30):

    cmd = [ADB, "-s", serial] + list(args)
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "adb command timed out"
    except Exception as e:
        return -1, "", str(e)

def _adb_shell(serial, cmd_str, timeout=30):
    rc, out, err = _adb(serial, "shell", cmd_str, timeout=timeout)
    return out

def _get_serial():
    return _read_file("/tmp/emulator_serial")

def _get_app_uid():
    return _read_file("/tmp/app_uid", "10110")

def _whisperd_pid(serial):
    out = _adb_shell(serial, "pgrep -x whisperd 2>/dev/null | head -1")
    return out.strip().replace("\r", "") or None

def _flag_present(serial):
    out = _adb_shell(serial, "ls /flag.txt 2>&1")
    return "No such file" not in out and "not found" not in out.lower()

def _backend_reachable():
    try:
        with urllib.request.urlopen(f"{BACKEND_LOCAL}/health", timeout=4) as r:
            return r.status == 200
    except Exception:
        return False

def _register_victim(handle=None, phone=None):

    h = handle if handle is not None else _current_handle()
    p = phone  if phone  is not None else _current_phone()
    pw = _current_password()
    payload = json.dumps({
        "phone": p,
        "handle": h,
        "display_name": _ENV_VICTIM_DISPLAY,
        "password": pw,
        "is_victim": True,
    }).encode()
    try:
        req = urllib.request.Request(
            f"{BACKEND_LOCAL}/auth/register",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            body = json.loads(r.read())
            return body.get("token", "")
    except Exception as e:
        log.warning("Victim registration failed: %s", e)
        return ""

def _write_flag(serial, flag_value):

    if not _FLAG_RE.match(flag_value):
        log.error(
            "Refusing to write flag: value does not match expected format "
            "(R3CTF{...}), got: %r", flag_value
        )
        return False

    src = "/data/local/tmp/.whisperflag"
    cmd = (

        f"(umask 077; printf '%s' '{flag_value}' > {src}) && "
        f"chmod 600 {src} && chown root:root {src} && "
        f"if ! grep -q ' /flag.txt ' /proc/mounts; then mount --bind {src} /flag.txt; fi"
    )
    rc, out, err = _adb(serial, "shell", cmd, timeout=15)
    if rc != 0:
        log.error("Flag write failed (rc=%d): %s", rc, err)
        return False

    rc2, readback, _ = _adb(serial, "shell", "cat /flag.txt", timeout=10)
    if rc2 != 0 or readback.strip() != flag_value:
        log.error(
            "Flag verify failed: readback=%r expected=%r", readback.strip(), flag_value
        )
        return False

    log.info("Flag written and verified on device")
    return True

def _ensure_whisperd(serial, app_uid):

    _adb_shell(serial, "pkill -x whisperd 2>/dev/null; true", timeout=10)
    time.sleep(1)
    _adb_shell(
        serial,
        f"( WHISPERD_APP_UID={app_uid} setsid /data/local/tmp/whisperd"
        f" >/data/local/tmp/whisperd.log 2>&1 </dev/null & ) ; sleep 1",
        timeout=15,
    )
    time.sleep(2)
    return _whisperd_pid(serial)

def _wait_app_ws_ready(serial, timeout=30):

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        out = _adb_shell(serial, "logcat -d 2>/dev/null | grep -m1 'WebSocket opened'",
                         timeout=8) or ""
        if "WebSocket opened" in out:
            return True
        time.sleep(2)
    return False

def _provision_app(serial, token, handle=None):

    h = handle if handle is not None else _current_handle()
    _adb_shell(serial, "am force-stop com.whisper.app 2>/dev/null || true", timeout=10)
    time.sleep(1)
    _adb_shell(serial, "logcat -c 2>/dev/null || true", timeout=8)
    if token:
        _adb_shell(
            serial,
            f"am start"
            f" -n com.whisper.app/.MainActivity"
            f" -a android.intent.action.MAIN"
            f" --es provision_token '{token}'"
            f" --es provision_backend '{DEVICE_BACKEND}'"
            f" --es provision_handle '{h}'",
            timeout=15,
        )
        ready = _wait_app_ws_ready(serial, timeout=30)
        log.info("app provision: WebSocket ready=%s", ready)
        return True
    else:
        _adb_shell(
            serial,
            "am start -n com.whisper.app/.MainActivity -a android.intent.action.MAIN",
            timeout=10,
        )
        _wait_app_ws_ready(serial, timeout=30)
        return False

def _acquire_watchdog_lock(timeout=20):

    try:
        fd = open(WATCHDOG_LOCK_PATH, "w")
    except OSError as e:
        log.warning("Cannot open watchdog lock file: %s", e)
        return None
    deadline = time.monotonic() + timeout
    while True:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fd
        except BlockingIOError:
            if time.monotonic() >= deadline:
                fd.close()
                return None
            time.sleep(0.25)

def _release_watchdog_lock(fd):
    try:
        fcntl.flock(fd, fcntl.LOCK_UN)
        fd.close()
    except Exception:
        pass

class Handler(http.server.BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        log.debug("HTTP %s", fmt % args)

    def _send_json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _check_admin_token(self):

        if not RUNNER_ADMIN_TOKEN:
            return True
        auth = self.headers.get("Authorization", "")
        if auth == f"Bearer {RUNNER_ADMIN_TOKEN}":
            return True
        self._send_json(401, {"error": "missing or invalid admin token"})
        return False

    def _read_body_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        try:
            raw = self.rfile.read(length)
            return json.loads(raw.decode("utf-8", errors="replace")) or {}
        except Exception:
            return {}

    def do_GET(self):
        if self.path == "/health":
            self._handle_health()
        else:
            self._send_json(404, {"error": "not found"})

    def do_POST(self):
        if self.path == "/reset":
            self._handle_reset()
        elif self.path == "/recycle":
            self._handle_recycle()
        else:
            self._send_json(404, {"error": "not found"})

    def _handle_health(self):
        serial = _get_serial()
        app_uid = _get_app_uid()

        boot_ok = False
        flag_ok = False
        wpid = None

        if serial:
            rc, out, _ = _adb(serial, "shell", "getprop sys.boot_completed")
            boot_ok = (out.strip() == "1")
            if boot_ok:
                flag_ok = _flag_present(serial)
                wpid = _whisperd_pid(serial)

        self._send_json(200, {
            "status": "ok",
            "service": "victim-runner",
            "instance_id": INSTANCE_ID,
            "victim_handle": _current_handle(),
            "boot": boot_ok,
            "serial": serial or "unknown",
            "app_uid": app_uid,
            "flag_present": flag_ok,
            "whisperd_pid": wpid,
        })

    def _handle_reset(self):

        if not self._check_admin_token():
            return

        if not _reset_lock.acquire(blocking=False):
            self._send_json(409, {"error": "reset already in progress"})
            return

        body = self._read_body_json()

        try:
            self._do_reset(body)
        finally:
            _reset_lock.release()

    def _do_reset(self, body):
        t0 = time.time()
        serial = _get_serial()
        app_uid = _get_app_uid()

        if not serial:
            self._send_json(503, {"error": "emulator serial not known; entrypoint may still be provisioning"})
            return

        new_handle = None
        new_phone  = None

        if isinstance(body, dict):
            raw_handle = body.get("victim_handle") or ""
            raw_phone  = body.get("victim_phone")  or ""
            if raw_handle:
                new_handle = raw_handle.strip()

                new_phone = raw_phone.strip() if raw_phone.strip() else _derive_phone(new_handle)

        new_flag = None
        if isinstance(body, dict):
            raw_flag = (body.get("flag") or "").strip()
            if raw_flag:
                if _FLAG_RE.match(raw_flag):
                    new_flag = raw_flag
                else:
                    self._send_json(400, {
                        "error": "invalid flag format: must match R3CTF{...}"
                    })
                    return

        new_password = None
        if new_handle and isinstance(body, dict):
            raw_pw = (body.get("victim_password") or "").strip()
            if raw_pw:
                new_password = raw_pw

        if new_handle:

            _persist_identity(new_handle, new_phone, password=new_password)
            log.info(
                "Reset: new lease identity handle=%s, phone=%s, password_set=%s",
                new_handle, new_phone, new_password is not None,
            )
        else:
            log.info("Reset: self-heal path -- using current handle=%s, persisted password",
                     _current_handle())

        handle = _current_handle()
        phone  = _current_phone()

        log.info("Reset starting (serial=%s, app_uid=%s, handle=%s)", serial, app_uid, handle)

        lock_fd = _acquire_watchdog_lock(timeout=20)
        if lock_fd is None:
            log.warning("Could not acquire watchdog lock within 20s; proceeding anyway.")

        try:
            _adb(serial, "root", timeout=15)
            time.sleep(2)
            _adb(serial, "wait-for-device", timeout=10)
            _adb_shell(serial, "setenforce 0 2>/dev/null || true", timeout=10)

            if not _flag_present(serial):
                self._send_json(500, {"error": "/flag.txt missing on device; full re-provision required"})
                return

            if new_flag:
                ok = _write_flag(serial, new_flag)
                if not ok:
                    self._send_json(500, {"error": "failed to write flag to device"})
                    return
            else:
                log.info("No flag in reset body; keeping baked /flag.txt")

            token = ""
            if _backend_reachable():
                token = _register_victim(handle=handle, phone=phone)
                if token:
                    log.info("Victim re-registered: handle=%s", handle)
                else:
                    log.warning("Victim re-registration failed; app will start without login")
            else:
                log.warning("Backend not reachable via socat; skipping victim registration")

            wpid = _whisperd_pid(serial)
            if not wpid:
                log.info("whisperd not running; restarting...")
                wpid = _ensure_whisperd(serial, app_uid)
            else:
                log.info("whisperd already running (pid=%s)", wpid)

            _provision_app(serial, token, handle=handle)
            log.info("App re-provisioned (handle=%s, token_present=%s)", handle, bool(token))

        finally:
            if lock_fd is not None:
                _release_watchdog_lock(lock_fd)

        elapsed = round(time.time() - t0, 1)
        log.info("Reset complete in %.1fs", elapsed)

        self._send_json(200, {
            "status": "reset",
            "instance_id": INSTANCE_ID,
            "serial": serial,
            "app_uid": app_uid,
            "whisperd_pid": wpid,
            "victim_handle": handle,
            "elapsed_s": elapsed,
        })

    def _handle_recycle(self):

        self._send_json(200, {"recycling": True})

        def _do_exit():
            time.sleep(1)
            log.info("Recycle requested -- exiting process so Docker restarts this container.")
            os._exit(0)

        t = threading.Thread(target=_do_exit, daemon=True)
        t.start()

if __name__ == "__main__":
    log.info("Control API starting on %s:%d", RUNNER_HOST, RUNNER_PORT)
    if RUNNER_ADMIN_TOKEN:
        log.info("/reset protected by RUNNER_ADMIN_TOKEN (%d chars)", len(RUNNER_ADMIN_TOKEN))
    else:
        log.info("/reset open to all callers on internal network (RUNNER_ADMIN_TOKEN not set)")
    server = http.server.HTTPServer((RUNNER_HOST, RUNNER_PORT), Handler)
    server.serve_forever()
