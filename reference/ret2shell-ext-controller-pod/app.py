import os
import sys

import requests
from flask import Flask, jsonify, render_template

_raw_team_id = os.environ.get("RET2SHELL_TEAM_ID")
CONTROLLER_URL = os.environ.get("CONTROLLER_URL", "").rstrip("/")

if not _raw_team_id:
    print("ERROR: RET2SHELL_TEAM_ID environment variable is required", file=sys.stderr)
    sys.exit(1)

try:
    TEAM_ID = int(_raw_team_id)
    if TEAM_ID < 0:
        raise ValueError("team id must be unsigned")
except ValueError as e:
    print(f"ERROR: RET2SHELL_TEAM_ID must be a valid uint64: {e}", file=sys.stderr)
    sys.exit(1)

if not CONTROLLER_URL:
    print("ERROR: CONTROLLER_URL environment variable is required", file=sys.stderr)
    sys.exit(1)

app = Flask(__name__)


def _forward(path: str, method: str = "GET", json_body=None):
    url = f"{CONTROLLER_URL}/api/{path}"
    headers = {
        "X-Team-ID": str(TEAM_ID),
        "Accept": "application/json",
    }
    try:
        resp = requests.request(
            method,
            url,
            headers=headers,
            timeout=10,
            json=json_body,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.exceptions.Timeout:
        return jsonify({"error": "controller timeout"}), 504
    except requests.exceptions.ConnectionError as e:
        return jsonify({"error": f"controller unreachable: {e}"}), 502
    except requests.exceptions.HTTPError as e:
        return jsonify({"error": f"controller error: {e}"}), resp.status_code
    except ValueError:
        return jsonify({"error": "invalid JSON from controller"}), 502

    # 只返回前端需要的字段，team_id 绝不暴露给前端
    return jsonify({
        "url": data.get("url"),
        "created_at": data.get("created_at"),
        "expires_at": data.get("expires_at"),
    })


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status", methods=["GET", "POST"])
def api_status():
    # 前端可以是 GET 或 POST，向后端发送的请求体为空；
    # 后端向 controller 转发时带 { team_id } 请求体。
    return _forward("status", "GET", json_body={"team_id": TEAM_ID})


@app.route("/api/create", methods=["POST"])
def api_create():
    return _forward("create", "POST", json_body={"team_id": TEAM_ID})


@app.route("/api/delete", methods=["POST"])
def api_delete():
    return _forward("delete", "POST", json_body={"team_id": TEAM_ID})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
