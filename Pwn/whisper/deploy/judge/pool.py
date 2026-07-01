import os
import json
import time
import secrets
import logging
import threading
from collections import deque
from typing import Optional

import requests
import flag_stego
import team_flags

logger = logging.getLogger("judge_pool")

def _load_pool_config():

    raw = os.environ.get("WHISPER_POOL", "[]")
    try:
        entries = json.loads(raw)
    except Exception:
        logger.error("WHISPER_POOL is not valid JSON: %r", raw)
        entries = []
    return entries

LEASE_SECONDS              = int(os.environ.get("LEASE_SECONDS", "900"))
LEASE_RATE_MAX             = int(os.environ.get("LEASE_RATE_MAX", "5"))
LEASE_COOLDOWN_SECS        = int(os.environ.get("LEASE_COOLDOWN_SECONDS", "60"))
REAPER_INTERVAL_SECS       = 5
INSTANCE_BOOT_DEADLINE_SECS = int(os.environ.get("INSTANCE_BOOT_DEADLINE_SECS", "1200"))

INSTANCE_BOOT_TYPICAL_SECS = int(os.environ.get("INSTANCE_BOOT_TYPICAL_SECS", "600"))

_PUBLIC_BACKEND_PORT  = os.environ.get("PUBLIC_BACKEND_PORT", "8000")
PUBLIC_BACKEND_URL    = (
    os.environ.get("PUBLIC_BACKEND_URL")
    or (
        "http://{}:{}".format(os.environ["PUBLIC_IP"], _PUBLIC_BACKEND_PORT)
        if os.environ.get("PUBLIC_IP")
        else os.environ.get("WHISPER_BACKEND_URL", "http://localhost:8000")
    )
)

_instances: dict = {}
_teams: dict = {}

_queue: deque = deque()

_lock = threading.RLock()

_pool_initialized = False

def _init_pool():
    global _pool_initialized
    with _lock:
        if _pool_initialized:
            return
        now = time.monotonic()
        for entry in _load_pool_config():
            iid = str(entry["id"])
            _instances[iid] = {
                "id": iid,
                "runner": entry["runner"],
                "victim": entry.get("victim", f"victim-{iid}"),
                "team": None,
                "expires_at": None,
                "current_handle": None,
                "current_phone": None,
                "lifecycle": "booting",
                "booting_since": now,
            }
        logger.info("Pool initialized: %d instances (all booting)", len(_instances))
        _pool_initialized = True

def _team_state(team: str) -> dict:

    if team not in _teams:
        _teams[team] = {
            "instance_id": None,
            "lease_expires_at": None,
            "release_at": None,
            "acquisitions": [],
            "victim_handle": None,
            "backend_url": None,
            "team_id": None,
            "current_flag": None,
            "current_password": None,
        }
    return _teams[team]

def _current_lease(team: str) -> Optional[dict]:

    ts = _team_state(team)
    iid = ts["instance_id"]
    if iid and _instances.get(iid, {}).get("team") == team:
        return _instances[iid]
    return None

def _free_instances() -> list:

    return [
        i for i in _instances.values()
        if i["lifecycle"] == "idle" and i["team"] is None
    ]

def _make_victim_identity() -> tuple:

    handle = "v" + secrets.token_hex(12)

    phone_suffix = str(secrets.randbelow(10 ** 9)).zfill(9)
    phone = "+1555" + phone_suffix
    return handle, phone

def _reset_runner(instance: dict):

    url = instance["runner"].rstrip("/") + "/reset"
    body = {
        "victim_handle": instance["current_handle"],
        "victim_phone":  instance["current_phone"],
    }
    if instance.get("flag"):
        body["flag"] = instance["flag"]
    if instance.get("victim_password"):
        body["victim_password"] = instance["victim_password"]
    try:
        resp = requests.post(url, json=body, timeout=30)
        resp.raise_for_status()
        logger.info(
            "Runner reset OK: instance %s via %s (handle=%s, flag_set=%s, password_set=%s)",
            instance["id"], url, instance["current_handle"],
            bool(instance.get("flag")), bool(instance.get("victim_password")),
        )
    except Exception as exc:
        logger.warning(
            "Runner reset FAILED for instance %s (%s): %s",
            instance["id"], url, exc
        )

def _recycle_runner(instance: dict):

    url = instance["runner"].rstrip("/") + "/recycle"
    try:
        resp = requests.post(url, timeout=10)
        resp.raise_for_status()
        logger.info(
            "Runner recycle triggered: instance %s via %s",
            instance["id"], url,
        )
    except Exception as exc:
        logger.warning(
            "Runner recycle FAILED for instance %s (%s): %s -- "
            "instance will stay booting; reaper will retry promotion when /health shows boot=true",
            instance["id"], url, exc,
        )

def _do_assign(team: str, instance: dict, team_id: int | None = None):

    now = time.time()
    ts = _team_state(team)

    handle, phone = _make_victim_identity()

    team_flag = None
    if team_id is not None:
        team_flag = team_flags.get(team_id)
        if team_flag is not None:
            logger.info("Using platform-pushed flag for team_id=%s", team_id)
        else:
            try:
                team_flag = flag_stego.make_flag(team_id)
            except Exception as exc:
                logger.error("flag_stego.make_flag(%s) failed: %s", team_id, exc)
                raise RuntimeError(
                    "per-team flag generation failed (team_id=%s): %s" % (team_id, exc)
                ) from exc

    lease_password = secrets.token_hex(16)

    ts["acquisitions"].append(now)
    ts["team_id"] = team_id
    ts["current_flag"] = team_flag
    ts["current_password"] = lease_password

    instance["team"] = team
    instance["expires_at"] = now + LEASE_SECONDS
    instance["current_handle"] = handle
    instance["current_phone"] = phone
    instance["lifecycle"] = "leased"
    instance["booting_since"] = None

    ts["instance_id"] = instance["id"]
    ts["lease_expires_at"] = instance["expires_at"]
    ts["release_at"] = None
    ts["victim_handle"] = handle
    ts["backend_url"] = PUBLIC_BACKEND_URL

    logger.info(
        "Assigned instance %s (handle=%s) to team %r (id=%s); expires in %ds",
        instance["id"], handle, team[:8] + "...", team_id, LEASE_SECONDS
    )

    inst_snapshot = dict(instance)
    if team_flag:
        inst_snapshot["flag"] = team_flag
    inst_snapshot["victim_password"] = lease_password

    threading.Thread(
        target=_reset_runner,
        args=(inst_snapshot,),
        daemon=True,
    ).start()

def _do_release(team: str, expired: bool = False) -> Optional[dict]:

    ts = _team_state(team)
    iid = ts["instance_id"]
    if iid is None:
        return None

    inst = _instances.get(iid)
    freed_inst = None
    if inst and inst["team"] == team:
        inst["team"] = None
        inst["expires_at"] = None
        freed_inst = inst

    ts["instance_id"] = None
    ts["lease_expires_at"] = None
    ts["release_at"] = time.time()
    ts["victim_handle"] = None
    ts["backend_url"] = None

    reason = "expired" if expired else "released"
    logger.info("Instance %s freed (%s) from team %r", iid, reason, team[:8] + "...")
    return freed_inst

def _promote_next():

    free = _free_instances()
    if not free or not _queue:
        return

    instance = free[0]

    while _queue:
        candidate = _queue[0]
        _queue.popleft()
        ts = _team_state(candidate)
        if ts["instance_id"] is not None:
            continue
        cooling, _ = _in_cooldown(candidate)
        if cooling:
            logger.info("Queue head %r is in cooldown, skipping", candidate[:8] + "...")
            continue

        _do_assign(candidate, instance, team_id=ts.get("team_id"))
        return

def _rate_limited(team: str) -> tuple:

    now = time.time()
    window_start = now - 3600
    ts = _team_state(team)
    ts["acquisitions"] = [t for t in ts["acquisitions"] if t > window_start]
    count = len(ts["acquisitions"])
    if count >= LEASE_RATE_MAX:
        oldest = ts["acquisitions"][0]
        retry_after = int(oldest + 3600 - now) + 1
        return True, retry_after
    return False, 0

def _in_cooldown(team: str) -> tuple:

    ts = _team_state(team)
    release_at = ts.get("release_at")
    if release_at is None:
        return False, 0
    elapsed = time.time() - release_at
    if elapsed < LEASE_COOLDOWN_SECS:
        left = int(LEASE_COOLDOWN_SECS - elapsed) + 1
        return True, left
    return False, 0

def _queue_position(team: str) -> int:

    for idx, t in enumerate(_queue):
        if t == team:
            return idx + 1
    return 0

def pool_lease(team: str, team_id: int | None = None) -> dict:

    _init_pool()
    with _lock:
        existing = _current_lease(team)
        if existing is not None:
            ts = _team_state(team)
            return {
                "leased": True,
                "instance_id": existing["id"],
                "victim_handle": ts["victim_handle"],
                "backend_url": ts["backend_url"],
                "expires_at": int(existing["expires_at"]),
                "seconds_left": max(0, int(existing["expires_at"] - time.time())),
            }

        pos = _queue_position(team)
        if pos > 0:

            _team_state(team)["team_id"] = team_id
            return {"queued": True, "position": pos, "pool_busy": True}

        is_limited, retry_after = _rate_limited(team)
        if is_limited:
            raise _RateLimitError(
                f"Acquisition rate limit: max {LEASE_RATE_MAX} leases per hour.",
                retry_after=retry_after,
                reason="rate_limited",
            )

        cooling, cooldown_left = _in_cooldown(team)
        if cooling:
            raise _RateLimitError(
                f"Cooldown active: wait {cooldown_left}s before re-leasing.",
                retry_after=cooldown_left,
                reason="cooldown",
            )

        free = _free_instances()
        if free:
            instance = free[0]
            _do_assign(team, instance, team_id=team_id)
            ts = _team_state(team)
            return {
                "leased": True,
                "instance_id": instance["id"],
                "victim_handle": ts["victim_handle"],
                "backend_url": ts["backend_url"],
                "expires_at": int(instance["expires_at"]),
                "seconds_left": LEASE_SECONDS,
            }

        _team_state(team)["team_id"] = team_id
        _queue.append(team)
        pos = _queue_position(team)
        logger.info("Team %r queued at position %d", team[:8] + "...", pos)
        return {"queued": True, "position": pos, "pool_busy": True}

def pool_release(team: str) -> dict:

    _init_pool()
    recycle_inst = None
    with _lock:
        existing = _current_lease(team)
        if existing is None:

            try:
                _queue.remove(team)
            except ValueError:
                pass
            return {"released": False, "message": "No active lease or queue slot."}

        freed_inst = _do_release(team, expired=False)

        if freed_inst is not None:

            freed_inst["lifecycle"] = "booting"
            freed_inst["booting_since"] = time.monotonic()
            freed_inst["current_handle"] = None
            freed_inst["current_phone"] = None
            recycle_inst = dict(freed_inst)
            logger.info(
                "Instance %s marked booting after release -- will recycle",
                freed_inst["id"],
            )

    if recycle_inst is not None:
        threading.Thread(
            target=_recycle_runner,
            args=(recycle_inst,),
            daemon=True,
        ).start()

    return {"released": True}

def _pool_counts() -> dict:

    total   = len(_instances)
    leased  = sum(1 for i in _instances.values() if i["lifecycle"] == "leased")
    idle    = sum(1 for i in _instances.values() if i["lifecycle"] == "idle")
    booting = sum(1 for i in _instances.values() if i["lifecycle"] == "booting")
    return {"total": total, "idle": idle, "leased": leased, "booting": booting}

def _est_wait_seconds(pos: int) -> int:

    now = time.time()
    mono_now = time.monotonic()

    earliest_lease_end = None
    for inst in _instances.values():
        if inst["lifecycle"] == "leased" and inst["expires_at"] is not None:
            left = inst["expires_at"] - now
            if earliest_lease_end is None or left < earliest_lease_end:
                earliest_lease_end = left

    boot_remaining = []
    for inst in _instances.values():
        if inst["lifecycle"] == "booting" and inst["booting_since"] is not None:
            elapsed = mono_now - inst["booting_since"]
            remaining = max(0, INSTANCE_BOOT_TYPICAL_SECS - elapsed)
            boot_remaining.append(remaining)

    candidates = []
    if earliest_lease_end is not None:
        candidates.append(max(30, int(earliest_lease_end)))
    if boot_remaining:
        avg_boot = int(sum(boot_remaining) / len(boot_remaining))
        candidates.append(max(30, avg_boot))
    if not candidates:
        candidates.append(INSTANCE_BOOT_TYPICAL_SECS)

    slot_time = min(candidates)
    return pos * slot_time

def pool_status(team: str) -> dict:

    _init_pool()
    with _lock:
        counts = _pool_counts()

        existing = _current_lease(team)
        if existing is not None:
            ts = _team_state(team)
            seconds_left = max(0, int(existing["expires_at"] - time.time()))
            return {
                "state": "leased",
                "instance_id": existing["id"],
                "victim_handle": ts["victim_handle"],
                "backend_url": ts.get("backend_url"),
                "expires_at": int(existing["expires_at"]),
                "seconds_left": seconds_left,
                **counts,
            }

        pos = _queue_position(team)
        if pos > 0:
            est_wait = _est_wait_seconds(pos)
            return {
                "state": "queued",
                "position": pos,
                "pool_busy": True,
                "est_wait_seconds": est_wait,
                **counts,
            }

        is_limited, rl_retry = _rate_limited(team)
        cooling, cooldown_left = _in_cooldown(team)
        status: dict = {
            "state": "idle",
            "rate_limited": is_limited,
            "in_cooldown": cooling,
            **counts,
        }
        if is_limited:
            status["retry_after_seconds"] = rl_retry
            status["reason"] = "rate_limited"
        elif cooling:
            status["retry_after_seconds"] = cooldown_left
            status["reason"] = "cooldown"
        return status

def pool_info() -> dict:

    _init_pool()
    with _lock:
        counts = _pool_counts()
        instances_summary = []
        mono_now = time.monotonic()
        for inst in _instances.values():
            entry = {
                "id": inst["id"],
                "lifecycle": inst["lifecycle"],
                "team_active": inst["team"] is not None,
                "current_handle": inst["current_handle"],
            }
            if inst["expires_at"] is not None:
                entry["seconds_left"] = max(0, int(inst["expires_at"] - time.time()))
            if inst["lifecycle"] == "booting" and inst.get("booting_since") is not None:
                entry["booting_elapsed_s"] = int(mono_now - inst["booting_since"])
            instances_summary.append(entry)

        return {
            "total_instances": counts["total"],
            "leased": counts["leased"],
            "idle": counts["idle"],
            "booting": counts["booting"],
            "free": counts["idle"],
            "queue_depth": len(_queue),
            "instances": instances_summary,
        }

class _RateLimitError(Exception):
    def __init__(self, message: str, retry_after: int, reason: str):
        super().__init__(message)
        self.retry_after = retry_after
        self.reason = reason

def _reaper_loop():

    logger.info("Pool reaper started (interval=%ds)", REAPER_INTERVAL_SECS)
    while True:
        time.sleep(REAPER_INTERVAL_SECS)
        try:
            _reaper_tick()
        except Exception as exc:
            logger.exception("Reaper error: %s", exc)

def _check_booting_health(instance_snapshot: dict) -> bool:

    url = instance_snapshot["runner"].rstrip("/") + "/health"
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            data = resp.json()
            return bool(data.get("boot", False))
    except Exception as exc:
        logger.debug("Health poll for instance %s failed: %s", instance_snapshot["id"], exc)
    return False

def _reaper_tick():
    now = time.time()
    mono_now = time.monotonic()
    recycle_instances = []
    booting_snapshots = []

    with _lock:

        expired_teams = [
            i["team"]
            for i in _instances.values()
            if i["lifecycle"] == "leased"
            and i["team"] is not None
            and i["expires_at"] is not None
            and now >= i["expires_at"]
        ]
        for team in expired_teams:
            logger.info("Lease expired for team %r -- releasing + recycling", team[:8] + "...")
            freed = _do_release(team, expired=True)
            if freed is not None:
                freed["lifecycle"] = "booting"
                freed["booting_since"] = mono_now
                freed["current_handle"] = None
                freed["current_phone"] = None
                recycle_instances.append(dict(freed))
                logger.info(
                    "Instance %s marked booting after expiry -- will recycle",
                    freed["id"],
                )

        for inst in _instances.values():
            if inst["lifecycle"] == "booting":
                elapsed = (
                    mono_now - inst["booting_since"]
                    if inst.get("booting_since") is not None
                    else 0
                )
                if elapsed > INSTANCE_BOOT_DEADLINE_SECS:
                    logger.warning(
                        "Instance %s has been booting for %ds (deadline=%ds) -- "
                        "still waiting; check the container logs.",
                        inst["id"], int(elapsed), INSTANCE_BOOT_DEADLINE_SECS,
                    )
                booting_snapshots.append(dict(inst))

        while _free_instances() and _queue:
            _promote_next()

    for recycle_inst in recycle_instances:
        threading.Thread(
            target=_recycle_runner,
            args=(recycle_inst,),
            daemon=True,
        ).start()

    for snap in booting_snapshots:
        booted = _check_booting_health(snap)
        if booted:
            with _lock:
                inst = _instances.get(snap["id"])
                if inst is not None and inst["lifecycle"] == "booting":
                    inst["lifecycle"] = "idle"
                    inst["booting_since"] = None
                    logger.info(
                        "Instance %s booted (health=true) -> lifecycle=idle",
                        inst["id"],
                    )

                    _promote_next()

def start_reaper():
    t = threading.Thread(target=_reaper_loop, daemon=True, name="pool-reaper")
    t.start()
    logger.info("Pool reaper thread launched")
    return t
