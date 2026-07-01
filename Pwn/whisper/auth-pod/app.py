"""whisper per-team auth pod (Model B).

One pod is spawned per team. Players authenticate to THIS pod with POD_TOKEN;
the pod talks to the (internal) whisper judge on the team's behalf. The judge is
never exposed to players.

Required env:
  TEAM_ID             numeric team id
  TEAM_TOKEN          team token for the judge (X-Team-Token); from teams.json
  POD_TOKEN           per-team token players use to reach this pod
  WHISPER_JUDGE_URL   internal judge base URL, e.g. http://whisper-judge:8080
  WHISPER_BACKEND_URL public messenger backend URL baked into the APK

Optional env:
  WHISPER_ADMIN_TOKEN admin token; required to push a platform flag at boot
  FLAG                platform-generated flag to push to the judge (Model A)
"""
import os
import sys
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
TEAM_TOKEN    = _need("TEAM_TOKEN")
POD_TOKEN     = _need("POD_TOKEN")
JUDGE_URL     = _need("WHISPER_JUDGE_URL").rstrip("/")
BACKEND_URL   = _need("WHISPER_BACKEND_URL").rstrip("/")
ADMIN_TOKEN   = os.environ.get("WHISPER_ADMIN_TOKEN", "").strip()
FLAG          = os.environ.get("FLAG", "").strip()

app = Flask(__name__)


def _authorized() -> bool:
    if request.headers.get("X-Pod-Token") == POD_TOKEN:
        return True
    if request.args.get("token") == POD_TOKEN:
        return True
    return False


def _team_headers() -> dict:
    return {"X-Team-Token": TEAM_TOKEN}


def push_flag() -> None:
    if not FLAG or not ADMIN_TOKEN:
        if FLAG:
            logger.warning("FLAG set but WHISPER_ADMIN_TOKEN missing; cannot push flag")
        return
    try:
        resp = requests.post(
            f"{JUDGE_URL}/admin/flags",
            json={"team_id": TEAM_ID, "flag": FLAG},
            headers={"X-Admin-Token": ADMIN_TOKEN},
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("pushed flag to judge for team_id=%s", TEAM_ID)
    except Exception as exc:
        logger.error("flag push failed: %s", exc)


def _proxy(method: str, path: str):
    if not _authorized():
        return jsonify({"error": "forbidden"}), 403
    url = f"{JUDGE_URL}{path}"
    try:
        resp = requests.request(
            method, url,
            headers=_team_headers(),
            timeout=25,
            json=request.get_json(silent=True),
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
