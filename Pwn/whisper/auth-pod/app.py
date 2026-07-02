"""whisper per-team auth pod.

One pod is spawned per team. Players authenticate to THIS pod with POD_TOKEN;
the pod talks to the (internal) whisper judge on the team's behalf. The judge is
never exposed to players.

Required env:
  TEAM_ID             numeric team id
  POD_TOKEN           per-team token players use to reach this pod
  WHISPER_JUDGE_URL   internal judge base URL, e.g. http://judge:8080
  WHISPER_BACKEND_URL public messenger backend URL baked into the APK
  WHISPER_ADMIN_TOKEN judge admin token (pod authenticates to judge with this)

Optional env:
  FLAG                platform flag to push to the judge (defaults to a test
                      placeholder if unset)
"""
import os
import sys
import time
import logging

import requests
from flask import Flask, Response, jsonify, render_template, request

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("auth-pod")


def _need(name: str) -> str:
    val = os.environ.get(name, "").strip()
    if not val:
        print(f"ERROR: {name} is required", file=sys.stderr)
        sys.exit(1)
    return val


TEAM_ID       = int(_need("TEAM_ID"))
POD_TOKEN     = _need("POD_TOKEN")
JUDGE_URL     = _need("WHISPER_JUDGE_URL").rstrip("/")
BACKEND_URL   = _need("WHISPER_BACKEND_URL").rstrip("/")
ADMIN_TOKEN   = _need("WHISPER_ADMIN_TOKEN")
FLAG          = os.environ.get("FLAG", "R3CTF{TEST_FLGA}").strip()

app = Flask(__name__)


def _authorized() -> bool:
    if request.headers.get("X-Pod-Token") == POD_TOKEN:
        return True
    if request.args.get("token") == POD_TOKEN:
        return True
    return False


def _admin_headers() -> dict:
    return {"X-Admin-Token": ADMIN_TOKEN}


def push_flag() -> bool:
    """Push this team's flag to the judge. Retries; returns True on success.

    The pod is the sole source of the team's flag, so this must succeed before
    the team can lease a victim. It is idempotent and safe to call repeatedly.
    """
    if not ADMIN_TOKEN:
        logger.error("WHISPER_ADMIN_TOKEN missing; cannot push flag")
        return False
    for attempt in range(1, 8):
        try:
            resp = requests.post(
                f"{JUDGE_URL}/admin/flags",
                json={"team_id": TEAM_ID, "flag": FLAG},
                headers={"X-Admin-Token": ADMIN_TOKEN},
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("pushed flag to judge for team_id=%s (attempt %d)", TEAM_ID, attempt)
            return True
        except Exception as exc:
            logger.warning("flag push attempt %d failed: %s", attempt, exc)
            time.sleep(min(2 * attempt, 10))
    logger.error("flag push failed after retries for team_id=%s", TEAM_ID)
    return False


def _proxy(method: str, path: str):
    if not _authorized():
        return jsonify({"error": "forbidden"}), 403
    url = f"{JUDGE_URL}{path}"
    try:
        resp = requests.request(
            method, url,
            headers=_admin_headers(),
            timeout=25,
            params={"team_id": TEAM_ID} if method == "GET" else None,
            json={"team_id": TEAM_ID} if method != "GET" else None,
        )
        try:
            return jsonify(resp.json()), resp.status_code
        except ValueError:
            return Response(resp.content, status=resp.status_code,
                            content_type=resp.headers.get("Content-Type"))
    except requests.exceptions.Timeout:
        return jsonify({"error": "judge timeout"}), 504
    except requests.exceptions.ConnectionError as exc:
        return jsonify({"error": f"judge unreachable: {exc}"}), 502


@app.route("/")
def index():
    if not _authorized():
        return jsonify({"error": "forbidden"}), 403
    return render_template("index.html", backend_url=BACKEND_URL, team_id=TEAM_ID)


@app.route("/lease", methods=["POST"])
def lease():
    if not _authorized():
        return jsonify({"error": "forbidden"}), 403
    # Make sure the judge has this team's flag before it leases a victim
    # (the judge refuses a lease for a team with no pushed flag).
    if not push_flag():
        return jsonify({"error": "could not register flag with judge; try again"}), 503
    return _proxy("POST", "/lease")


@app.route("/release", methods=["POST"])
def release():
    return _proxy("POST", "/release")


@app.route("/status", methods=["GET"])
def status():
    return _proxy("GET", "/status")


@app.route("/download/whisper.apk")
def download_apk():
    if not _authorized():
        return jsonify({"error": "forbidden"}), 403
    try:
        resp = requests.get(
            f"{JUDGE_URL}/download/whisper.apk",
            headers=_team_headers(), timeout=60, stream=True,
        )
        resp.raise_for_status()
    except Exception as exc:
        return jsonify({"error": f"apk fetch failed: {exc}"}), 502
    return Response(
        resp.iter_content(chunk_size=64 * 1024),
        content_type="application/vnd.android.package-archive",
        headers={"Content-Disposition": "attachment; filename=whisper.apk"},
    )


if __name__ == "__main__":
    push_flag()
    app.run(host="0.0.0.0", port=5000)
