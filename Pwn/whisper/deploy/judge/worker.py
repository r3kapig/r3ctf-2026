import os
import re
import time
import uuid
import json
import logging
import subprocess
import threading
import queue

import requests
import team_flags
from whisper_deliver import register_account, poll_messages

logger = logging.getLogger("judge_worker")

FLAG_RE = re.compile(r"R3CTF\{[^}]+\}")

BACKEND_URL      = os.environ.get("WHISPER_BACKEND_URL", "http://localhost:8000")
ADMIN_TOKEN      = os.environ.get("WHISPER_ADMIN_TOKEN", "ctf-admin-token")
VICTIM_HANDLE    = os.environ.get("WHISPER_VICTIM_HANDLE", "victim")
VICTIM_PHONE     = os.environ.get("WHISPER_VICTIM_PHONE", "+15550000")
RESET_SCRIPT     = os.environ.get("WHISPER_RESET_SCRIPT", "")
CF_RUNNER_URL    = os.environ.get("WHISPER_CF_RUNNER_URL", "")
ATTEMPT_TIMEOUT  = int(os.environ.get("WHISPER_ATTEMPT_TIMEOUT", "180"))
REAL_FLAG        = os.environ.get("WHISPER_REAL_FLAG", "")

def _flag_accepted(candidate: str, team_id: int | None = None) -> bool:

    if not FLAG_RE.match(candidate):
        return False

    if team_id is not None:
        pushed = team_flags.get(team_id)
        if pushed is None:
            logger.error("No flag pushed for team_id=%s; rejecting", team_id)
            return False
        # The flag was pushed by the auth pod and is authoritative for the team;
        # the scoring platform handles flag-sharing / stegano validation.
        return candidate == pushed

    if REAL_FLAG:
        return candidate == REAL_FLAG

    logger.error(
        "No validation configured (no team_id and WHISPER_REAL_FLAG unset): rejecting. "
        "Per-team flags are validated by the scoring platform, not the judge."
    )
    return False

SCAN_PHONE    = os.environ.get("WHISPER_SCAN_PHONE", "+15559002")
SCAN_HANDLE   = os.environ.get("WHISPER_SCAN_HANDLE", "judge_scanner")
SCAN_PASSWORD = os.environ.get("WHISPER_SCAN_PASSWORD", "judge-scan-wh1sper-2026")

MODE_PLAYER = "player"

_attempt_queue: queue.Queue = queue.Queue(maxsize=20)
_results: dict[str, dict] = {}
_results_lock = threading.Lock()

_pending_flags: dict[str, str] = {}
_flags_lock = threading.Lock()

def _reset_backend(logs):

    resp = requests.post(
        f"{BACKEND_URL}/admin/reset",
        headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        timeout=15,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Backend reset failed {resp.status_code}: {resp.text}")
    logs.append("Backend reset OK")
    logger.info("Backend reset OK")

def _reset_victim(logs):

    if CF_RUNNER_URL:
        resp = requests.post(f"{CF_RUNNER_URL}/reset", timeout=180)
        resp.raise_for_status()
        logs.append("Victim reset via cuttlefish-runner")
        logger.info("Cuttlefish victim reset via runner API")
        return

    if RESET_SCRIPT and os.path.isfile(RESET_SCRIPT):
        env = os.environ.copy()
        if REAL_FLAG:
            env["WHISPER_REAL_FLAG"] = REAL_FLAG
        result = subprocess.run(
            [RESET_SCRIPT],
            env=env,
            timeout=180,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Reset script failed: {result.stderr[:500]}")
        logs.append("Victim reset via script OK")
        logger.info("Victim reset via script OK")
        return

    logs.append("No victim reset configured (dev mode)")
    logger.warning("No victim reset configured; using dev mode (backend reset only)")

def _wait_for_victim_ready(logs, timeout: int = 90):

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = requests.get(f"{BACKEND_URL}/health", timeout=5)
            if resp.status_code == 200:

                victim_resp = requests.post(
                    f"{BACKEND_URL}/auth/register",
                    json={
                        "phone": VICTIM_PHONE,
                        "password": "probe-unused",
                        "handle": VICTIM_HANDLE,
                        "display_name": "Whisper Victim",
                    },
                    timeout=10,
                )
                if victim_resp.status_code in (200, 409):
                    logs.append("Victim account ready")
                    logger.info(
                        "Victim account ready on backend (probe status=%d)",
                        victim_resp.status_code,
                    )
                    return
        except Exception as exc:
            logger.debug("Waiting for backend/victim: %s", exc)
        time.sleep(3)
    raise TimeoutError("Victim not ready after reset")

def _scan_all_conversations_for_flag(
    token: str,
    after_ts: int,
    timeout: int,
    poll_interval: float = 3.0,
    team_id: int | None = None,
) -> str | None:

    deadline = time.time() + timeout
    logger.info("Player mode: scanning all conversations for flag (timeout=%ds)", timeout)
    while time.time() < deadline:
        try:
            r = requests.get(
                f"{BACKEND_URL}/conversations",
                headers={"Authorization": f"Bearer {token}"},
                timeout=10,
            )
            r.raise_for_status()
            for conv in r.json():
                cid = conv["id"]
                msgs = poll_messages(BACKEND_URL, token, cid, after_ts=after_ts - 10)
                for msg in msgs:
                    body = msg.get("body") or ""
                    m = FLAG_RE.search(body)
                    if m:
                        if _flag_accepted(m.group(0), team_id=team_id):
                            logger.info("Flag captured in conversation %s: [REDACTED]", cid)
                            return m.group(0)
                        else:
                            logger.info(
                                "Flag candidate in conversation %s did not pass validation; skipping",
                                cid,
                            )
        except Exception as exc:
            logger.warning("Scan error: %s", exc)
        time.sleep(poll_interval)
    return None

def _run_attempt(attempt_id: str, mode: str, payload: bytes | None,
                 team_id: int | None = None):
    logs: list[str] = []

    def log(msg: str):
        logs.append(msg)
        logger.info("[%s] %s", attempt_id, msg)

    def _finalize(solved: bool, flag: str | None = None):
        with _results_lock:
            _results[attempt_id] = {
                "attempt_id": attempt_id,
                "solved": solved,
                "mode": mode,
                "log": list(logs),
                "finished_at": int(time.time()),
            }
        if solved and flag:
            with _flags_lock:
                _pending_flags[attempt_id] = flag
            log("Solve confirmed (flag stored for one-time retrieval)")
        else:
            log("Attempt finished: no flag captured")

    try:
        log(f"Attempt starting (mode={mode})")

        log("Player mode: attaching scanner to live backend")
        try:
            creds = register_account(
                BACKEND_URL, SCAN_PHONE, SCAN_HANDLE, "Judge Scanner",
                password=SCAN_PASSWORD,
            )
            scan_token = creds["token"]
        except Exception as exc:
            log(f"Scanner account error: {exc}")
            _finalize(solved=False)
            return

        provision_ts = int(time.time())
        log(f"Backend ready at {BACKEND_URL}; victim handle: {VICTIM_HANDLE}")

        with _results_lock:
            if attempt_id in _results:
                _results[attempt_id]["backend_url"] = BACKEND_URL
                _results[attempt_id]["victim_handle"] = VICTIM_HANDLE

        flag = _scan_all_conversations_for_flag(
            scan_token, after_ts=provision_ts, timeout=ATTEMPT_TIMEOUT,
            team_id=team_id,
        )
        _finalize(solved=bool(flag), flag=flag)

    except Exception as exc:
        logger.exception("[%s] Worker error: %s", attempt_id, exc)
        with _results_lock:
            _results[attempt_id] = {
                "attempt_id": attempt_id,
                "solved": False,
                "mode": mode,
                "log": logs + [f"Internal error: {type(exc).__name__}"],
                "finished_at": int(time.time()),
            }

def worker_loop():

    logger.info("Judge worker started")
    while True:
        item = _attempt_queue.get()

        if len(item) == 4:
            attempt_id, mode, payload, team_id = item
        else:
            attempt_id, mode, payload = item
            team_id = None
        logger.info("Processing attempt %s (mode=%s, team_id=%s)", attempt_id, mode, team_id)
        _run_attempt(attempt_id, mode, payload, team_id=team_id)
        _attempt_queue.task_done()

def _enqueue(mode: str, payload: bytes | None = None,
             team_id: int | None = None) -> str:

    attempt_id = str(uuid.uuid4())
    with _results_lock:
        _results[attempt_id] = {
            "attempt_id": attempt_id,
            "solved": False,
            "mode": mode,
            "log": ["Queued"],
            "finished_at": None,
        }
    _attempt_queue.put_nowait((attempt_id, mode, payload, team_id))
    return attempt_id

def enqueue_player_attempt(team_id: int | None = None) -> str:

    return _enqueue(MODE_PLAYER, payload=None, team_id=team_id)

def get_result(attempt_id: str) -> dict | None:

    with _results_lock:
        result = _results.get(attempt_id)
    if result is None:
        return None

    result = dict(result)

    if result.get("solved"):
        with _flags_lock:
            flag = _pending_flags.pop(attempt_id, None)
        if flag:
            result["flag"] = flag

    return result

def queue_depth() -> int:
    return _attempt_queue.qsize()

def start_worker():
    t = threading.Thread(target=worker_loop, daemon=True)
    t.start()
    return t
