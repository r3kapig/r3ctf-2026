import os
import signal
import socket
import sys
import threading

from flask import Flask, Response, jsonify, render_template

CONTROLLER_HOST = os.environ.get("CONTROLLER_HOST", "").strip()
CONTROLLER_PORT = int(os.environ.get("CONTROLLER_PORT", "8888"))
_raw_team_id = os.environ.get("RET2SHELL_TEAM_ID")

if not CONTROLLER_HOST:
    print("ERROR: CONTROLLER_HOST environment variable is required", file=sys.stderr)
    sys.exit(1)
if not _raw_team_id:
    print("ERROR: RET2SHELL_TEAM_ID environment variable is required", file=sys.stderr)
    sys.exit(1)
try:
    TEAM_ID = int(_raw_team_id)
    if not -(2 ** 63) <= TEAM_ID < 2 ** 63:
        raise ValueError("team id out of range")
except ValueError as e:
    print(f"ERROR: RET2SHELL_TEAM_ID must be a valid i64: {e}", file=sys.stderr)
    sys.exit(1)

BEGIN = b"-----BEGIN KUBECONFIG-----"
END = b"-----END KUBECONFIG-----"

_state_lock = threading.Lock()
_state = {"status": "connecting", "kubeconfig": None, "error": None}
_sock = None


def _set(**kw):
    with _state_lock:
        _state.update(kw)


def _bridge():
    """Open one nc connection to the controller, hand it the team id, read the
    returned kubeconfig, then hold the connection open for the pod's lifetime so
    the controller keeps the per-team cluster alive."""
    global _sock
    try:
        s = socket.create_connection((CONTROLLER_HOST, CONTROLLER_PORT), timeout=30)
    except OSError as e:
        _set(status="error", error=f"cannot reach controller: {e}")
        return
    _sock = s
    s.sendall(f"{TEAM_ID}\n".encode())

    buf = b""
    s.settimeout(600)  # control-plane provisioning streams progress dots meanwhile
    try:
        while END not in buf:
            chunk = s.recv(4096)
            if not chunk:
                _set(status="error", error="controller closed before sending kubeconfig")
                return
            buf += chunk
    except OSError as e:
        _set(status="error", error=f"read failed: {e}")
        return

    start = buf.find(BEGIN)
    end = buf.find(END)
    if start == -1 or end == -1 or end < start:
        _set(status="error", error="kubeconfig markers not found")
        return
    kubeconfig = buf[start + len(BEGIN):end].decode(errors="replace").strip("\n") + "\n"
    _set(status="ready", kubeconfig=kubeconfig)
    print("=" * 60, flush=True)
    print(kubeconfig, flush=True)
    print("=" * 60, flush=True)

    s.settimeout(None)
    try:
        while s.recv(4096):
            pass
    except OSError:
        pass
    _set(status="disconnected")


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/status")
def api_status():
    with _state_lock:
        return jsonify({
            "status": _state["status"],
            "kubeconfig": _state["kubeconfig"],
            "error": _state["error"],
        })


@app.route("/kubeconfig")
def kubeconfig():
    with _state_lock:
        kc = _state["kubeconfig"]
    if not kc:
        return Response("kubeconfig not ready\n", status=409, mimetype="text/plain")
    return Response(
        kc,
        mimetype="application/yaml",
        headers={"Content-Disposition": "attachment; filename=kubeconfig.yaml"},
    )


def _shutdown(signum, frame):
    if _sock is not None:
        try:
            _sock.close()
        except OSError:
            pass
    sys.exit(0)


signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

threading.Thread(target=_bridge, daemon=True).start()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
