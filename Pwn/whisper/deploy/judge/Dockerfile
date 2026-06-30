# judge-web -- Whisper CTF judge container.
#
# Additions over base python:3.11-slim:
#   - default-jre-headless  (keytool for keystore generation)
#   - apksigner + zipalign  (from Android build-tools; copied from host or apt)
#   - a fixed debug keystore generated at build time
#
# APK signing uses a fixed debug keystore so the baked APK is reproducible
# across container restarts (important: teams that already downloaded the APK
# should get the same signature on reinstall).
#
# Build-arg: ANDROID_BUILD_TOOLS_DIR (default /opt/android-tools-host)
# The orchestrator copies the needed binaries there before building:
#   zipalign, apksigner.jar, lib/apksigner.jar dependencies (or the shim)
# If those are not present, apt fallback is used (slower but self-contained).

FROM python:3.11-slim

# ---- System packages -------------------------------------------------------
# default-jre-headless: provides keytool and java (for apksigner.jar wrapper)
# apksigner / zipalign: apt packages if available (Android SDK is not in apt on
#   standard Debian; we use the bundled binaries from build-args when available)
RUN apt-get update && apt-get install -y --no-install-recommends \
    default-jre-headless \
    zipalign \
    apksigner \
    curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Python deps -----------------------------------------------------------
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- App code --------------------------------------------------------------
COPY . .

# ---- Android tools ---------------------------------------------------------
# Create the standard tool dir. If the Dockerfile build context includes
# pre-copied build-tools binaries, they land here and take priority over apt.
# The apk.py _find_tool() checks /opt/android-tools/<name> first.
RUN mkdir -p /opt/android-tools

# Copy host build-tools binaries if they were placed in the build context.
# (Optional: the build can proceed without them; apt versions are used instead.)
# The orchestrator should COPY them to deploy/android-build-tools/ before building.
# COPY deploy/android-build-tools/ /opt/android-tools/    # uncomment if available

# ---- Debug keystore --------------------------------------------------------
# Generate a fixed debug keystore at build time. The alias, passwords, and DN
# are the same as the standard Android debug.keystore so tools work with it.
# PKCS12 format (java 9+). Valid for 30 years.
RUN keytool -genkeypair \
      -keystore /opt/android-tools/debug.keystore \
      -storetype PKCS12 \
      -alias androiddebugkey \
      -keyalg RSA \
      -keysize 2048 \
      -validity 10950 \
      -storepass android \
      -keypass android \
      -dname "CN=Android Debug,O=Android,C=US" \
    && echo "Debug keystore generated at /opt/android-tools/debug.keystore"

# ---- Runtime env -----------------------------------------------------------
ENV PYTHONUNBUFFERED=1
ENV WHISPER_BACKEND_URL=http://backend:8000
ENV WHISPER_ADMIN_TOKEN=ctf-admin-token
ENV WHISPER_VICTIM_HANDLE=victim
ENV WHISPER_ATTEMPT_TIMEOUT=120
ENV WHISPER_MAX_RCARD_BYTES=4194304
# Pool config -- override in docker-compose.yml with the real runner URLs
ENV WHISPER_POOL='[]'
# Teams file (mount deploy/config/teams.json here)
ENV WHISPER_TEAMS_FILE=/config/teams.json
# APK paths
ENV WHISPER_TEMPLATE_APK=/app/dist/whisper.apk
ENV JUDGE_BAKED_APK_DIR=/tmp/whisper_baked
ENV JUDGE_DEBUG_KEYSTORE=/opt/android-tools/debug.keystore
ENV JUDGE_KEYSTORE_PASS=android
# Lease config
ENV LEASE_SECONDS=900
ENV LEASE_RATE_MAX=5
ENV LEASE_COOLDOWN_SECONDS=60
# judge-web listens on 8080
ENV JUDGE_HOST=0.0.0.0
ENV JUDGE_PORT=8080

EXPOSE 8080

# Default: run judge-web (includes embedded worker + pool reaper threads)
CMD ["python", "web.py"]
