import os
import re
import time
import logging
import requests

ATTACKER_PASSWORD = os.environ.get("WHISPER_ATTACKER_PASSWORD", "judge-att-wh1sper-2026")

logger = logging.getLogger("whisper_deliver")

FLAG_RE = re.compile(r"R3CTF\{[^}]+\}")

def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def register_account(
    backend_url: str,
    phone: str,
    handle: str,
    display_name: str,
    password: str = "",
) -> dict:

    if not password:
        password = ATTACKER_PASSWORD
    resp = requests.post(
        f"{backend_url}/auth/register",
        json={
            "phone": phone,
            "password": password,
            "handle": handle,
            "display_name": display_name,
        },
        timeout=10,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"register failed {resp.status_code}: {resp.text}")
    return resp.json()

def upload_rcard(backend_url: str, token: str, rcard_bytes: bytes, filename: str = "payload.rcard") -> dict:

    resp = requests.post(
        f"{backend_url}/attachments/upload",
        data=rcard_bytes,
        headers={
            **_headers(token),
            "Content-Type": "application/octet-stream",
            "X-Filename": filename,
            "X-Kind": "rcard",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()

def open_dm(backend_url: str, token: str, target: str) -> str:

    resp = requests.post(
        f"{backend_url}/conversations/dm",
        params={"target_user_id": target},
        headers=_headers(token),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()["conversation_id"]

def send_rcard_dm(backend_url: str, token: str, conversation_id: str, attachment_id: str) -> dict:

    resp = requests.post(
        f"{backend_url}/messages",
        json={
            "conversation_id": conversation_id,
            "type": "attachment",
            "body": None,
            "attachment_id": attachment_id,
            "reply_to_id": None,
        },
        headers=_headers(token),
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()

def poll_messages(backend_url: str, token: str, conversation_id: str, after_ts: int = 0) -> list:

    resp = requests.get(
        f"{backend_url}/conversations/{conversation_id}/messages",
        params={"limit": 200},
        headers=_headers(token),
        timeout=10,
    )
    resp.raise_for_status()
    msgs = resp.json()
    return [m for m in msgs if m.get("created_at", 0) > after_ts]

def deliver_rcard(backend_url: str, attacker_token: str, victim_handle: str, rcard_bytes: bytes) -> tuple:

    attachment = upload_rcard(backend_url, attacker_token, rcard_bytes)
    attachment_id = attachment["id"]
    logger.info("Uploaded attachment %s (%d bytes)", attachment_id, len(rcard_bytes))

    conv_id = open_dm(backend_url, attacker_token, victim_handle)
    logger.info("Conversation with victim: %s", conv_id)

    send_ts = int(time.time())
    msg = send_rcard_dm(backend_url, attacker_token, conv_id, attachment_id)
    logger.info("Sent rcard DM message_id=%s", msg["id"])

    return conv_id, attachment_id, send_ts

def wait_for_flag(
    backend_url: str,
    attacker_token: str,
    conversation_id: str,
    after_ts: int = 0,
    timeout: int = 120,
    poll_interval: float = 2.0,
    expected: str | None = None,
) -> str | None:

    deadline = time.time() + timeout
    logger.info("Watching conversation %s for flag (timeout=%ds)", conversation_id, timeout)
    while time.time() < deadline:
        try:
            msgs = poll_messages(backend_url, attacker_token, conversation_id, after_ts)
            for msg in msgs:
                body = msg.get("body") or ""
                m = FLAG_RE.search(body)
                if m:
                    candidate = m.group(0)
                    if expected is None or candidate == expected:
                        logger.info("Flag captured: [REDACTED]")
                        return candidate
                    else:
                        logger.info("non-matching flag in conversation; skipping [REDACTED]")
        except Exception as exc:
            logger.warning("Poll error: %s", exc)
        time.sleep(poll_interval)
    logger.warning("Timed out waiting for flag after %ds", timeout)
    return None

class AttemptResult:
    def __init__(self, solved: bool, flag: str | None = None, log: list | None = None):
        self.solved = solved
        self.flag = flag
        self.log = log or []

    def as_dict(self, reveal_flag: bool = False) -> dict:
        d: dict = {"solved": self.solved, "log": self.log}
        if self.solved and reveal_flag:
            d["flag"] = self.flag
        return d

def full_attempt(
    backend_url: str,
    attacker_phone: str,
    attacker_handle: str,
    victim_handle: str,
    rcard_bytes: bytes,
    timeout: int = 120,
    expected_flag: str | None = None,
) -> AttemptResult:

    logs: list[str] = []

    def log(msg: str):
        logs.append(msg)
        logger.info(msg)

    try:
        log("Registering attacker account")
        creds = register_account(backend_url, attacker_phone, attacker_handle, attacker_handle)
        attacker_token = creds["token"]
        log(f"Attacker registered: handle={attacker_handle}")

        log("Uploading .rcard and sending DM to victim")
        conv_id, attachment_id, send_ts = deliver_rcard(
            backend_url, attacker_token, victim_handle, rcard_bytes
        )
        log(f"DM sent: conversation={conv_id}")

        log(f"Watching for flag (timeout={timeout}s)")
        flag = wait_for_flag(
            backend_url, attacker_token, conv_id,
            after_ts=send_ts - 5, timeout=timeout,
            expected=expected_flag,
        )

        if flag:
            log("Solve confirmed")
            return AttemptResult(solved=True, flag=flag, log=logs)
        else:
            log("Timeout: no flag received")
            return AttemptResult(solved=False, log=logs)

    except Exception as exc:
        log(f"Attempt error: {type(exc).__name__}: {exc}")
        return AttemptResult(solved=False, log=logs)
