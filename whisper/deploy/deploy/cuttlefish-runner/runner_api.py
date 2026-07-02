import os
import subprocess
import logging
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("runner_api")

app = Flask(__name__)

REAL_FLAG        = os.environ.get("WHISPER_REAL_FLAG", "")
APK_PATH         = os.environ.get("WHISPER_APK_PATH", "/runner/dist/whisper.apk")
WHISPERD_PATH    = os.environ.get("WHISPER_WHISPERD_PATH", "/runner/whisperd/out/android/x86_64/whisperd")
RESET_SCRIPT     = os.environ.get("WHISPER_RESET_SCRIPT", "/runner/aosp/reset_victim.sh")
HOST             = os.environ.get("RUNNER_HOST", "0.0.0.0")
PORT             = int(os.environ.get("RUNNER_PORT", "9090"))

@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "cuttlefish-runner"})

@app.post("/reset")
def reset():

    if not REAL_FLAG:
        logger.error("WHISPER_REAL_FLAG not set; cannot provision real flag")
        return jsonify({"error": "WHISPER_REAL_FLAG not configured"}), 500

    env = os.environ.copy()
    env["WHISPER_REAL_FLAG"] = REAL_FLAG

    cmd = [
        RESET_SCRIPT,
        "--apk", APK_PATH,
        "--whisperd", WHISPERD_PATH,
        "--flag", REAL_FLAG,
    ]
    logger.info("Running victim reset: %s", " ".join(cmd))
    try:
        result = subprocess.run(
            cmd,
            env=env,
            timeout=300,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        logger.error("Reset script timed out")
        return jsonify({"error": "Reset timed out"}), 500

    if result.returncode != 0:

        safe_stderr = result.stderr[:1000].replace(REAL_FLAG, "[FLAG]")
        logger.error("Reset script failed: %s", safe_stderr)
        return jsonify({"error": "Reset failed", "detail": safe_stderr}), 500

    logger.info("Victim reset complete")
    return jsonify({"status": "ready"})

if __name__ == "__main__":
    app.run(host=HOST, port=PORT)
