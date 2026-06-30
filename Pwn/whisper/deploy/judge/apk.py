import io
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
import logging
import urllib.parse

logger = logging.getLogger("judge_apk")

_CONFIG_ENTRY = "assets/whisper_config.json"

def _find_tool(name: str) -> str:

    env_key = "JUDGE_" + name.upper().replace("-", "_")
    override = os.environ.get(env_key)
    if override and os.path.isfile(override):
        return override

    bundled = f"/opt/android-tools/{name}"
    if os.path.isfile(bundled):
        return bundled

    found = shutil.which(name)
    if found:
        return found

    raise RuntimeError(
        f"Tool '{name}' not found. Set {env_key} env var or install it. "
        "See judge/Dockerfile for the expected install path."
    )

def _replace_zip_entry(src_bytes: bytes, entry_name: str, new_content: bytes) -> bytes:

    buf = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(src_bytes), "r") as src_zip, \
         zipfile.ZipFile(buf, "w", allowZip64=True) as out_zip:

        for info in src_zip.infolist():
            if info.filename == entry_name:
                continue

            data = src_zip.read(info.filename)
            info2 = zipfile.ZipInfo(info.filename, date_time=info.date_time)
            info2.compress_type = info.compress_type
            info2.comment = info.comment
            info2.extra = info.extra
            out_zip.writestr(info2, data)

        config_info = zipfile.ZipInfo(_CONFIG_ENTRY)
        config_info.compress_type = zipfile.ZIP_STORED
        out_zip.writestr(config_info, new_content)

    return buf.getvalue()

def _run(cmd: list, description: str):
    logger.debug("Running: %s", " ".join(str(x) for x in cmd))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{description} failed (exit {result.returncode}):\n"
            f"stdout: {result.stdout.strip()}\n"
            f"stderr: {result.stderr.strip()}"
        )

def bake_apk(template: str, backend_url: str, out: str, keystore: str) -> None:

    t_start = __import__("time").monotonic()

    zipalign = _find_tool("zipalign")
    apksigner = _find_tool("apksigner")

    parsed = urllib.parse.urlparse(backend_url)
    host_port = parsed.netloc
    ws_url = f"ws://{host_port}"
    config = json.dumps({"backend": backend_url, "ws": ws_url}, separators=(",", ":"))
    config_bytes = config.encode("utf-8")
    logger.info("Baking APK: backend=%s ws=%s", backend_url, ws_url)

    if not os.path.isfile(template):
        raise FileNotFoundError(f"Template APK not found: {template}")
    with open(template, "rb") as fh:
        template_bytes = fh.read()

    patched_bytes = _replace_zip_entry(template_bytes, _CONFIG_ENTRY, config_bytes)

    with tempfile.TemporaryDirectory(prefix="whisper_bake_") as tmpdir:
        unaligned = os.path.join(tmpdir, "unaligned.apk")
        aligned   = os.path.join(tmpdir, "aligned.apk")

        with open(unaligned, "wb") as fh:
            fh.write(patched_bytes)

        _run([zipalign, "-f", "4", unaligned, aligned], "zipalign")

        ks_pass = os.environ.get("JUDGE_KEYSTORE_PASS", "android")
        _run([
            apksigner, "sign",
            "--ks", keystore,
            "--ks-pass", f"pass:{ks_pass}",
            "--out", out,
            aligned,
        ], "apksigner sign")

    elapsed = __import__("time").monotonic() - t_start
    logger.info("APK baked to %s in %.1fs", out, elapsed)

def verify_apk(path: str) -> bool:

    try:
        apksigner = _find_tool("apksigner")
        result = subprocess.run(
            [apksigner, "verify", "--verbose", path],
            capture_output=True, text=True
        )
        ok = result.returncode == 0
        if ok:
            logger.info("APK signature verified: %s", path)
        else:
            logger.warning("APK signature verification failed: %s", result.stderr.strip())
        return ok
    except Exception as exc:
        logger.warning("apksigner verify error: %s", exc)
        return False

def config_in_apk(path: str) -> dict | None:

    try:
        with zipfile.ZipFile(path, "r") as zf:
            if _CONFIG_ENTRY not in zf.namelist():
                return None
            raw = zf.read(_CONFIG_ENTRY)
            return json.loads(raw)
    except Exception:
        return None
