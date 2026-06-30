import hashlib
import hmac
import json
import logging
import os
import sys
import time
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
import uvicorn

import worker as judge_worker
import pool as judge_pool
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
SESSION_SECRET    = os.environ.get("JUDGE_SESSION_SECRET", ADMIN_TOKEN + "-session")

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

import base64

def _sign_session(token: str) -> str:
    b64 = base64.urlsafe_b64encode(token.encode()).decode()
    sig = hmac.new(SESSION_SECRET.encode(), b64.encode(), hashlib.sha256).hexdigest()
    return f"{b64}.{sig}"

def _verify_session(cookie: str) -> str | None:

    try:
        b64, sig = cookie.rsplit(".", 1)
    except ValueError:
        return None
    expected = hmac.new(SESSION_SECRET.encode(), b64.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        token = base64.urlsafe_b64decode(b64).decode()
    except Exception:
        return None

    if _team_name(token) is None:
        return None
    return token

def _team_token_from_request(request: Request) -> str | None:

    xt = request.headers.get("X-Team-Token", "").strip()
    if xt and _team_name(xt) is not None:
        return xt

    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        candidate = auth[len("Bearer "):]
        if candidate != ADMIN_TOKEN and _team_name(candidate) is not None:
            return candidate

    cookie_val = request.cookies.get("whisper_session", "")
    if cookie_val:
        return _verify_session(cookie_val)

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

@app.post("/login")
async def login(request: Request, response: Response):

    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        token = body.get("token", "").strip()
    else:
        form = await request.form()
        token = str(form.get("token", "")).strip()

    name = _team_name(token)
    if name is None:

        return HTMLResponse(content=_login_page(error="Invalid team token."), status_code=401)

    cookie_val = _sign_session(token)
    resp = RedirectResponse(url="/", status_code=303)
    resp.set_cookie(
        "whisper_session",
        cookie_val,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
    )
    return resp

@app.post("/logout")
async def logout(request: Request):
    resp = RedirectResponse(url="/", status_code=303)
    resp.delete_cookie("whisper_session")
    return resp

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

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    token = _team_token_from_request(request)
    if token is None:
        return HTMLResponse(content=_login_page(), status_code=200)

    name  = _team_name(token) or "Unknown Team"
    state = judge_pool.pool_status(token)
    return HTMLResponse(content=_dashboard_page(token, name, state), status_code=200)

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

@app.get("/result/{attempt_id}")
def get_result(attempt_id: str):

    result = judge_worker.get_result(attempt_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown attempt_id")
    return JSONResponse(result)

_FONT_STACK = "-apple-system, 'Segoe UI', Roboto, Inter, sans-serif"
_MONO_STACK = "'JetBrains Mono', 'Fira Mono', 'Consolas', monospace"

_CSS = f"""
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

:root {{
  --bg:          #07080D;
  --glass:       rgba(17,19,27,.72);
  --glass-soft:  rgba(255,255,255,.05);
  --glass-line:  rgba(255,255,255,.08);
  --grad:        linear-gradient(135deg,#FF8A5B,#FF4D88,#B15CFF);
  --accent:      #FF5C8A;
  --teal:        #3DD9C0;
  --text:        #F2F3F8;
  --dim:         #9AA0B4;
  --faint:       #5C6376;
  --radius-lg:   18px;
  --radius-md:   12px;
  --radius-sm:   8px;
  --shadow:      0 8px 40px rgba(0,0,0,.55);
}}

html, body {{
  height: 100%;
  font-family: {_FONT_STACK};
  background: var(--bg);
  color: var(--text);
  font-size: 15px;
  line-height: 1.6;
  -webkit-font-smoothing: antialiased;
}}

/* Aurora background blobs */
.aurora {{
  position: fixed; inset: 0; z-index: 0; overflow: hidden; pointer-events: none;
}}
.aurora-blob {{
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.18;
  animation: drift linear infinite;
}}
.aurora-blob:nth-child(1) {{
  width: 520px; height: 520px;
  background: #FF5C8A;
  top: -120px; left: -80px;
  animation-duration: 22s;
}}
.aurora-blob:nth-child(2) {{
  width: 420px; height: 420px;
  background: #B15CFF;
  bottom: -100px; right: -60px;
  animation-duration: 27s;
  animation-direction: reverse;
}}
.aurora-blob:nth-child(3) {{
  width: 340px; height: 340px;
  background: #FF8A5B;
  top: 40%; left: 55%;
  animation-duration: 19s;
}}
@keyframes drift {{
  0%   {{ transform: translate(0, 0) scale(1); }}
  33%  {{ transform: translate(30px, -40px) scale(1.04); }}
  66%  {{ transform: translate(-20px, 30px) scale(0.97); }}
  100% {{ transform: translate(0, 0) scale(1); }}
}}

/* Layout */
.page {{
  position: relative; z-index: 1;
  min-height: 100vh;
  display: flex; flex-direction: column; align-items: center;
}}

/* Topbar */
.topbar {{
  width: 100%;
  display: flex; align-items: center; justify-content: space-between;
  padding: 18px 28px;
  border-bottom: 1px solid var(--glass-line);
  background: rgba(7,8,13,.60);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  position: sticky; top: 0; z-index: 10;
}}
.brand {{
  display: flex; align-items: center; gap: 10px;
  font-size: 1.15rem; font-weight: 700; letter-spacing: -.01em;
}}
.brand-mark {{
  width: 32px; height: 32px; border-radius: 9px;
  background: var(--grad);
  display: flex; align-items: center; justify-content: center;
  font-size: 14px; color: #fff; font-weight: 800; flex-shrink: 0;
  box-shadow: 0 2px 12px rgba(177,92,255,.35);
}}
.brand-name {{
  background: var(--grad);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
}}
.topbar-right {{
  display: flex; align-items: center; gap: 12px;
  color: var(--dim); font-size: 0.88rem;
}}
.team-label {{
  font-weight: 600; color: var(--text);
  max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}

/* Container */
.container {{
  width: 100%; max-width: 680px;
  padding: 40px 20px 80px;
  flex: 1;
}}

/* Glass card */
.card {{
  background: var(--glass);
  border: 1px solid var(--glass-line);
  border-radius: var(--radius-lg);
  padding: 28px 32px;
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  box-shadow: var(--shadow);
}}

/* Buttons */
.btn {{
  display: inline-flex; align-items: center; justify-content: center; gap: 8px;
  padding: 11px 24px;
  border-radius: var(--radius-md);
  font-size: 0.92rem; font-weight: 600;
  cursor: pointer; border: none; text-decoration: none;
  transition: opacity .15s, transform .1s;
  font-family: inherit;
}}
.btn:active {{ transform: scale(.97); }}
.btn:focus-visible {{ outline: 2px solid var(--accent); outline-offset: 3px; }}

.btn-primary {{
  background: var(--grad); color: #fff;
  box-shadow: 0 4px 20px rgba(255,77,136,.28);
}}
.btn-primary:hover {{ opacity: .88; }}
.btn-primary:disabled {{
  background: rgba(255,255,255,.08); color: var(--faint);
  cursor: not-allowed; box-shadow: none;
}}

.btn-ghost {{
  background: var(--glass-soft);
  border: 1px solid var(--glass-line);
  color: var(--dim);
}}
.btn-ghost:hover {{ color: var(--text); border-color: rgba(255,255,255,.18); }}

.btn-danger {{
  background: rgba(231,76,60,.15);
  border: 1px solid rgba(231,76,60,.3);
  color: #e74c3c;
}}
.btn-danger:hover {{ background: rgba(231,76,60,.25); }}

.btn-icon {{
  padding: 7px 14px;
  font-size: 0.8rem;
  border-radius: var(--radius-sm);
  background: var(--glass-soft);
  border: 1px solid var(--glass-line);
  color: var(--dim); cursor: pointer; font-family: {_MONO_STACK};
  transition: background .15s, color .15s;
}}
.btn-icon:hover {{ background: rgba(255,255,255,.1); color: var(--text); }}

/* Input */
.input {{
  width: 100%;
  background: var(--glass-soft);
  border: 1px solid var(--glass-line);
  border-radius: var(--radius-md);
  padding: 12px 16px;
  font-size: 0.95rem; color: var(--text); font-family: inherit;
  outline: none; transition: border-color .15s;
}}
.input::placeholder {{ color: var(--faint); }}
.input:focus {{ border-color: rgba(255,92,138,.55); }}

/* Labels and values */
.field-label {{
  font-size: 0.75rem; text-transform: uppercase; letter-spacing: .07em;
  color: var(--faint); margin-bottom: 6px;
}}
.field-row {{
  display: flex; align-items: center; gap: 10px;
  background: var(--glass-soft);
  border: 1px solid var(--glass-line);
  border-radius: var(--radius-md);
  padding: 10px 14px;
}}
.field-val {{
  flex: 1; font-family: {_MONO_STACK}; font-size: 0.88rem;
  color: var(--text); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}

/* Status dot */
.status-row {{
  display: flex; align-items: center; gap: 10px; margin-bottom: 24px;
}}
.dot {{
  width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(255,255,255,.08);
}}
.dot-green  {{ background: #3DD9C0; box-shadow: 0 0 8px #3DD9C0; }}
.dot-yellow {{ background: #f39c12; }}
.dot-gray   {{ background: var(--faint); }}
.dot-red    {{ background: #e74c3c; }}
.status-text {{ font-weight: 600; font-size: 0.95rem; }}

/* Countdown */
.countdown {{
  font-family: {_MONO_STACK};
  font-size: 2.4rem; font-weight: 700;
  background: var(--grad);
  -webkit-background-clip: text; background-clip: text;
  -webkit-text-fill-color: transparent;
  line-height: 1;
}}
.countdown-label {{
  font-size: 0.78rem; color: var(--dim); margin-top: 4px; text-transform: uppercase;
  letter-spacing: .06em;
}}

/* Queue spinner */
@keyframes pulse {{
  0%, 100% {{ opacity: 1; }}
  50%       {{ opacity: .35; }}
}}
.pulse-dot {{
  width: 8px; height: 8px; border-radius: 50%;
  display: inline-block; margin: 0 3px;
  animation: pulse 1.4s ease-in-out infinite;
}}
.pulse-dot:nth-child(2) {{ animation-delay: .2s; }}
.pulse-dot:nth-child(3) {{ animation-delay: .4s; }}

/* Divider */
.divider {{ border: none; border-top: 1px solid var(--glass-line); margin: 24px 0; }}

/* Notice */
.notice {{
  font-size: 0.82rem; color: var(--dim); line-height: 1.5;
}}
.notice a {{ color: var(--accent); text-decoration: none; }}
.notice a:hover {{ text-decoration: underline; }}

/* Error text */
.err-text {{ color: #e74c3c; font-size: 0.88rem; margin-top: 10px; }}

/* Tagline */
.tagline {{ color: var(--dim); font-size: 0.92rem; }}

/* Stack utility */
.stack {{ display: flex; flex-direction: column; gap: 16px; }}
.stack-sm {{ display: flex; flex-direction: column; gap: 10px; }}

/* Copied feedback (JS-managed) */
.copy-ok {{ color: var(--teal) !important; }}

@media (max-width: 480px) {{
  .card {{ padding: 22px 18px; }}
  .topbar {{ padding: 14px 16px; }}
  .countdown {{ font-size: 1.8rem; }}
}}
"""

_COPY_JS = """
function copyField(id, btn) {
  var el = document.getElementById(id);
  if (!el) return;
  var text = el.getAttribute('data-val') || el.innerText || el.textContent;
  var orig = btn.textContent;
  navigator.clipboard.writeText(text).then(function() {
    btn.textContent = 'Copied!';
    btn.classList.add('copy-ok');
    setTimeout(function() {
      btn.textContent = orig;
      btn.classList.remove('copy-ok');
    }, 1500);
  }).catch(function() {
    var ta = document.createElement('textarea');
    ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
    document.body.appendChild(ta); ta.select(); document.execCommand('copy');
    document.body.removeChild(ta);
    btn.textContent = 'Copied!';
    setTimeout(function() { btn.textContent = orig; }, 1500);
  });
}
"""

def _page_shell(title: str, body: str, topbar_html: str = "") -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="aurora">
  <div class="aurora-blob"></div>
  <div class="aurora-blob"></div>
  <div class="aurora-blob"></div>
</div>
<div class="page">
{topbar_html}
{body}
</div>
<script>{_COPY_JS}</script>
</body>
</html>"""

def _topbar(team_name: str) -> str:
    safe_name = team_name.replace("<", "&lt;").replace(">", "&gt;")
    return f"""
<header class="topbar">
  <div class="brand">
    <div class="brand-mark">W</div>
    <span class="brand-name">Whisper</span>
  </div>
  <div class="topbar-right">
    <span class="team-label">{safe_name}</span>
    <form method="POST" action="/logout" style="display:inline;">
      <button type="submit" class="btn btn-ghost" style="padding:7px 16px;font-size:.82rem;">Sign out</button>
    </form>
  </div>
</header>"""

def _login_page(error: str = "") -> str:
    err_html = f'<p class="err-text">{error}</p>' if error else ""
    body = f"""
<div class="container" style="display:flex;align-items:center;justify-content:center;padding-top:80px;">
  <div class="card" style="width:100%;max-width:420px;">
    <div style="text-align:center;margin-bottom:28px;">
      <div class="brand-mark" style="width:48px;height:48px;border-radius:14px;font-size:22px;margin:0 auto 16px;">W</div>
      <div style="font-size:1.6rem;font-weight:700;background:var(--grad);-webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:6px;">Whisper</div>
      <div class="tagline">Mobile pwn challenge</div>
    </div>
    {err_html}
    <form method="POST" action="/login" class="stack-sm">
      <div>
        <div class="field-label">Team access token</div>
        <input class="input" type="password" name="token"
               placeholder="Paste your token here" autocomplete="off" autofocus>
      </div>
      <button type="submit" class="btn btn-primary" style="width:100%;margin-top:6px;">Enter</button>
    </form>
    <hr class="divider">
    <p class="notice">Tokens are issued per team at registration. Contact the organizers if you have not received yours.</p>
  </div>
</div>"""
    return _page_shell("Whisper CTF", body)

def _dashboard_page(token: str, team_name: str, state: dict) -> str:
    s = state.get("state", "idle")

    if s == "leased":
        seconds_left  = state.get("seconds_left", 0)
        victim_handle = state.get("victim_handle", "")
        be_url        = state.get("backend_url", PUBLIC_BACKEND_URL)
        expires_at    = state.get("expires_at", 0)

        safe_handle = victim_handle.replace("<", "&lt;").replace(">", "&gt;")
        safe_url    = be_url.replace("<", "&lt;").replace(">", "&gt;")

        panel = f"""
<div class="card">
  <div class="status-row">
    <div class="dot dot-green"></div>
    <span class="status-text">Instance active</span>
  </div>

  <div class="stack">
    <div>
      <div class="field-label">Target handle</div>
      <div class="field-row">
        <span class="field-val" id="field-handle" data-val="{victim_handle}">{safe_handle}</span>
        <button class="btn-icon" onclick="copyField('field-handle',this)">Copy</button>
      </div>
    </div>

    <div>
      <div class="field-label">Flag format</div>
      <div class="field-row">
        <span class="field-val" id="field-flag" data-val="R3CTF{{...}}">R3CTF{{...}}</span>
      </div>
    </div>

    <div>
      <div class="field-label">Download app</div>
      <a class="btn btn-ghost" href="/download/whisper.apk" style="align-self:flex-start;">
        Download whisper.apk
      </a>
    </div>
  </div>

  <hr class="divider">

  <div style="margin-bottom:20px;">
    <div class="field-label">Lease expires in</div>
    <div class="countdown" id="countdown">{_fmt_countdown(seconds_left)}</div>
    <div class="countdown-label">mm : ss</div>
  </div>

  <button type="button" class="btn btn-danger" id="btn-release"
    onclick="this.disabled=true;this.textContent='Releasing…';fetch('/release',{{method:'POST',credentials:'include'}}).then(function(){{location.reload();}}).catch(function(){{location.reload();}});">
    Release instance
  </button>
</div>
<script>
(function() {{
  var secs = {seconds_left};
  var el = document.getElementById('countdown');
  function fmt(s) {{
    var m = Math.floor(s / 60);
    var ss = s % 60;
    return (m < 10 ? '0' : '') + m + ':' + (ss < 10 ? '0' : '') + ss;
  }}
  var t = setInterval(function() {{
    secs--;
    if (secs <= 0) {{
      el.textContent = '00:00';
      clearInterval(t);
      // Poll /status to confirm expiry then reload
      setTimeout(function() {{ window.location.reload(); }}, 2000);
      return;
    }}
    el.textContent = fmt(secs);
  }}, 1000);
  // Keep state fresh: poll /status every 10s; on expiry reload
  setInterval(function() {{
    fetch('/status', {{credentials:'include'}})
      .then(function(r) {{
        if (r.status === 401) {{ window.location.href = '/'; return; }}
        return r.json();
      }})
      .then(function(d) {{
        if (!d) return;
        if (d.state !== 'leased') {{ window.location.reload(); }}
        else {{
          secs = d.seconds_left;
          el.textContent = fmt(secs);
        }}
      }})
      .catch(function() {{}});
  }}, 10000);
}})();
</script>"""

    elif s == "queued":
        pos          = state.get("position", "?")
        booting_cnt  = state.get("booting", 0)
        idle_cnt     = state.get("idle", 0)
        est_wait     = state.get("est_wait_seconds", 0)
        total_cnt    = state.get("total", state.get("total_instances", "?"))

        if booting_cnt > 0 and idle_cnt == 0:
            status_detail = (
                f"Preparing a fresh instance ({booting_cnt} device"
                f"{'s' if booting_cnt != 1 else ''} booting)..."
            )
        else:
            status_detail = (
                f"All {total_cnt} instance"
                f"{'s are' if total_cnt != 1 else ' is'} in use."
            )

        if est_wait > 0:
            if est_wait >= 120:
                eta_str = f"~{est_wait // 60} min"
            else:
                eta_str = f"~{est_wait}s"
            eta_html = (
                f'<p style="color:var(--faint);font-size:0.82rem;margin-top:8px;">'
                f'Estimated wait: <strong style="color:var(--dim);">{eta_str}</strong>'
                f"</p>"
            )
        else:
            eta_html = ""

        panel = f"""
<div class="card">
  <div class="status-row">
    <div class="dot dot-yellow"></div>
    <span class="status-text">Waiting in queue</span>
  </div>
  <p style="color:var(--dim);margin-bottom:6px;">
    {status_detail}
    You are at position <strong id="queue-pos" style="color:var(--text);">{pos}</strong>.
    You will be assigned automatically when a slot opens.
  </p>
  {eta_html}
  <div style="margin-top:20px;">
    <span class="pulse-dot" style="background:var(--accent);"></span>
    <span class="pulse-dot" style="background:var(--accent);"></span>
    <span class="pulse-dot" style="background:var(--accent);"></span>
  </div>
</div>
<script>
(function() {{
  var lastBooting = {int(booting_cnt > 0 and idle_cnt == 0)};
  setInterval(function() {{
    fetch('/status', {{credentials:'include'}})
      .then(function(r) {{
        if (r.status === 401) {{ window.location.href = '/'; return; }}
        return r.json();
      }})
      .then(function(d) {{
        if (!d) return;
        if (d.state !== 'queued') {{
          window.location.reload();
          return;
        }}
        // Update position label if the DOM element exists
        var posEl = document.getElementById('queue-pos');
        if (posEl && d.position !== undefined) posEl.textContent = d.position;
        // Reload if the booting/idle mix changed so status line updates
        var nowBooting = (d.booting > 0 && d.idle === 0) ? 1 : 0;
        if (nowBooting !== lastBooting) {{
          window.location.reload();
        }}
      }})
      .catch(function() {{}});
  }}, 4000);
}})();
</script>"""

    else:

        limited  = state.get("rate_limited", False)
        cooling  = state.get("in_cooldown", False)
        retry_s  = state.get("retry_after_seconds", 0)
        reason   = state.get("reason", "")

        if limited or cooling:
            if reason == "rate_limited":
                notice_text = f"You have reached the maximum number of instances per hour. Try again in {retry_s}s."
            else:
                notice_text = f"Cooldown active: {retry_s}s remaining before you can request another instance."

            panel = f"""
<div class="card">
  <div class="status-row">
    <div class="dot dot-red"></div>
    <span class="status-text">Rate limited</span>
  </div>
  <p style="color:var(--dim);margin-bottom:16px;">{notice_text}</p>
  <div class="countdown" id="cd-rl" style="font-size:1.6rem;">{_fmt_countdown(retry_s)}</div>
</div>
<script>
(function() {{
  var secs = {retry_s};
  var el = document.getElementById('cd-rl');
  function fmt(s) {{
    var m = Math.floor(s/60); var ss = s%60;
    return (m<10?'0':'')+m+':'+(ss<10?'0':'')+ss;
  }}
  var t = setInterval(function() {{
    secs--;
    if (secs <= 0) {{ clearInterval(t); window.location.reload(); return; }}
    el.textContent = fmt(secs);
  }}, 1000);
}})();
</script>"""
        else:
            panel = f"""
<div class="card">
  <div class="status-row">
    <div class="dot dot-gray"></div>
    <span class="status-text">No active instance</span>
  </div>
  <p class="notice" style="margin-bottom:24px;">
    Spin up a fresh target device to attack. Each instance has an isolated victim account
    with a randomized handle visible only to your team.
  </p>
  <button type="button" class="btn btn-primary" id="btn-lease"
    onclick="this.disabled=true;this.textContent='Requesting…';fetch('/lease',{{method:'POST',credentials:'include'}}).then(function(){{location.reload();}}).catch(function(){{location.reload();}});">
    Request instance
  </button>
  <div style="height:1px;background:rgba(255,255,255,0.08);margin:24px 0;"></div>
  <div class="field-label">Download app</div>
  <a class="btn btn-ghost" href="/download/whisper.apk" style="align-self:flex-start;">
    Download whisper.apk
  </a>
</div>"""

    safe_team = team_name.replace("<", "&lt;").replace(">", "&gt;")
    body = f"""
<div class="container">
  <div style="margin-bottom:24px;">
    <h1 style="font-size:1.05rem;color:var(--dim);font-weight:500;">
      Welcome, <span style="color:var(--text);font-weight:700;">{safe_team}</span>
    </h1>
  </div>
  {panel}
</div>"""

    return _page_shell(f"Whisper CTF - {team_name}", body, _topbar(team_name))

def _fmt_countdown(seconds: int) -> str:

    m = seconds // 60
    s = seconds % 60
    return f"{m:02d}:{s:02d}"

if __name__ == "__main__":
    uvicorn.run("web:app", host=JUDGE_HOST, port=JUDGE_PORT, reload=False)
