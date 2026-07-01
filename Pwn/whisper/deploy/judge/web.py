import json
import logging
import os
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

import worker as judge_worker
import pool as judge_pool
import team_flags
from pool import _RateLimitError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("judge_web")

ADMIN_TOKEN       = os.environ.get("WHISPER_ADMIN_TOKEN", "ctf-admin-token")
JUDGE_HOST        = os.environ.get("JUDGE_HOST", "0.0.0.0")
JUDGE_PORT        = int(os.environ.get("JUDGE_PORT", "8080"))
BACKEND_URL       = os.environ.get("WHISPER_BACKEND_URL", "http://localhost:8000")
VICTIM_HANDLE     = os.environ.get("WHISPER_VICTIM_HANDLE", "victim")
MAX_RCARD_BYTES   = int(os.environ.get("WHISPER_MAX_RCARD_BYTES", str(4 * 1024 * 1024)))
TEAMS_FILE        = os.environ.get("WHISPER_TEAMS_FILE", "/config/teams.json")

_HERE         = Path(__file__).parent.resolve()
_REPO_ROOT    = _HERE.parent
TEMPLATE_APK  = os.environ.get("WHISPER_TEMPLATE_APK", str(_REPO_ROOT / "dist" / "whisper.apk"))
BAKED_APK_DIR = os.environ.get("JUDGE_BAKED_APK_DIR", "/tmp/whisper_baked")
DEBUG_KEYSTORE = os.environ.get("JUDGE_DEBUG_KEYSTORE", "/opt/android-tools/debug.keystore")

PUBLIC_BACKEND_URL = judge_pool.PUBLIC_BACKEND_URL

def _load_teams() -> dict:

    try:
        with open(TEAMS_FILE) as fh:
            data = json.load(fh)
        teams = {}
        for idx, entry in enumerate(data.get("teams", []), start=1):
            tok = entry.get("token", "").strip()
            name = entry.get("name", "Unknown Team")
            team_id = int(entry.get("id", idx))
            if tok:
                teams[tok] = {"name": name, "id": team_id}
        logger.info("Loaded %d teams from %s", len(teams), TEAMS_FILE)
        return teams
    except FileNotFoundError:
        logger.warning("Teams file not found: %s -- team auth disabled", TEAMS_FILE)
        return {}
    except Exception as exc:
        logger.error("Failed to load teams file: %s", exc)
        return {}

_teams_registry: dict = {}
_teams_lock = threading.Lock()

def _get_teams() -> dict:
    with _teams_lock:
        return dict(_teams_registry)

def _reload_teams():
    global _teams_registry
    with _teams_lock:
        _teams_registry = _load_teams()

def _team_name(token: str) -> str | None:

    entry = _get_teams().get(token)
    if entry is None:
        return None
    return entry["name"]

def _team_id(token: str) -> int | None:

    entry = _get_teams().get(token)
    if entry is None:
        return None
    return entry["id"]

def _team_token_from_request(request: Request) -> str | None:

    xt = request.headers.get("X-Team-Token", "").strip()
    if xt and _team_name(xt) is not None:
        return xt

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        candidate = auth[len("Bearer "):]
        if candidate != ADMIN_TOKEN and _team_name(candidate) is not None:
            return candidate

    return None

def _require_team(request: Request) -> str:

    token = _team_token_from_request(request)
    if token is None:
        raise HTTPException(
            status_code=401,
            detail="Team token required. Log in at / or send X-Team-Token header.",
        )
    return token

def _require_admin(request: Request):
    auth_header = request.headers.get("Authorization", "")
    x_token     = request.headers.get("X-Admin-Token", "")
    provided    = None
    if auth_header.startswith("Bearer "):
        provided = auth_header[len("Bearer "):]
    elif x_token:
        provided = x_token
    if provided is None:
        raise HTTPException(status_code=401, detail="Admin token required.")
    if provided != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token.")

def _is_admin(request: Request) -> bool:
    try:
        _require_admin(request)
        return True
    except HTTPException:
        return False

_baked_apk_path: str | None = None
_baked_backend_url: str | None = None
_apk_lock = threading.Lock()
_apk_available = False

def _bake_apk_cached():

    global _baked_apk_path, _baked_backend_url, _apk_available

    with _apk_lock:
        if _baked_backend_url == PUBLIC_BACKEND_URL and _baked_apk_path and \
                os.path.isfile(_baked_apk_path):
            return

        os.makedirs(BAKED_APK_DIR, exist_ok=True)
        out_path = os.path.join(BAKED_APK_DIR, "whisper.apk")

        if not os.path.isfile(TEMPLATE_APK):
            logger.warning("Template APK not found at %s -- download unavailable", TEMPLATE_APK)
            _apk_available = False
            return

        try:
            from apk import bake_apk
            bake_apk(TEMPLATE_APK, PUBLIC_BACKEND_URL, out_path, DEBUG_KEYSTORE)
            _baked_apk_path   = out_path
            _baked_backend_url = PUBLIC_BACKEND_URL
            _apk_available    = True
            logger.info("APK baked OK -> %s (backend=%s)", out_path, PUBLIC_BACKEND_URL)
        except Exception as exc:
            logger.error("APK bake failed: %s -- serving template as fallback", exc)
            _baked_apk_path   = TEMPLATE_APK
            _baked_backend_url = PUBLIC_BACKEND_URL
            _apk_available    = True

@asynccontextmanager
async def lifespan(app: FastAPI):
    _reload_teams()
    judge_worker.start_worker()
    judge_pool.start_reaper()
    judge_pool._init_pool()
    logger.info("Judge worker + pool reaper started")

    threading.Thread(target=_bake_apk_cached, daemon=True, name="apk-bake").start()
    yield

app = FastAPI(title="Whisper CTF Judge", docs_url=None, redoc_url=None, lifespan=lifespan)

@app.get("/health")
def health(request: Request):

    base = {"status": "ok", "service": "whisper-judge"}
    if _is_admin(request):
        base["pool"] = judge_pool.pool_info()
        base["worker_queue_depth"] = judge_worker.queue_depth()
    return base

@app.get("/download/whisper.apk")
def download_apk():

    with _apk_lock:
        path = _baked_apk_path
        available = _apk_available

    if not available or not path or not os.path.isfile(path):
        raise HTTPException(
            status_code=503,
            detail="APK not ready yet. Try again in a few seconds.",
        )
    return FileResponse(
        path,
        media_type="application/vnd.android.package-archive",
        filename="whisper.apk",
    )

@app.post("/lease")
async def lease(request: Request):

    token = _require_team(request)
    tid = _team_id(token)
    try:
        result = judge_pool.pool_lease(token, team_id=tid)
    except _RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "error": str(exc),
                "retry_after": exc.retry_after,
                "reason": exc.reason,
            },
        )
    return JSONResponse(result)

@app.post("/release")
async def release(request: Request):

    token = _require_team(request)
    result = judge_pool.pool_release(token)
    return JSONResponse(result)

@app.get("/status")
async def status(request: Request):

    token = _require_team(request)
    result = judge_pool.pool_status(token)
    return JSONResponse(result)

@app.post("/attempt/provision")
async def provision_attempt(request: Request):

    _require_admin(request)
    try:
        attempt_id = judge_worker.enqueue_player_attempt()
    except Exception:
        raise HTTPException(status_code=503, detail="Queue full; try again later")
    return JSONResponse({
        "attempt_id": attempt_id,
        "status": "queued",
        "mode": "player",
        "backend_url": BACKEND_URL,
        "victim_handle": VICTIM_HANDLE,
    })

@app.post("/submit")
async def submit(request: Request):

    _require_admin(request)
    raw = await request.body()
    if raw and not raw.startswith(b"RCRD") and len(raw) < MAX_RCARD_BYTES:
        raise HTTPException(status_code=400, detail="Invalid .rcard magic (expected 'RCRD')")
    if len(raw) > MAX_RCARD_BYTES:
        raise HTTPException(status_code=413, detail=f"Payload too large (max {MAX_RCARD_BYTES} bytes)")
    try:
        attempt_id = judge_worker.enqueue_player_attempt()
    except Exception:
        raise HTTPException(status_code=503, detail="Queue full; try again later")
    return JSONResponse({"attempt_id": attempt_id, "status": "queued"})

@app.post("/admin/flags")
async def admin_set_flag(request: Request):

    # A per-team auth pod pushes its team's flag here so the victim uses the
    # platform-generated flag (validated by the scoring platform).
    _require_admin(request)
    body = await request.json()
    team_id = int(body["team_id"])
    flag = str(body["flag"])
    team_flags.set(team_id, flag)
    logger.info("admin_set_flag: team_id=%s (flag redacted)", team_id)
    return JSONResponse({"ok": True, "team_id": team_id})

@app.get("/result/{attempt_id}")
def get_result(attempt_id: str):

    result = judge_worker.get_result(attempt_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown attempt_id")
    return JSONResponse(result)

if __name__ == "__main__":
    uvicorn.run("web:app", host=JUDGE_HOST, port=JUDGE_PORT, reload=False)
