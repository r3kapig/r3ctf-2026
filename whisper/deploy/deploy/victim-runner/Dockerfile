# victim-runner/Dockerfile
#
# Boots a goldfish android-34 x86_64 AVD inside a KVM-privileged container,
# bakes /flag.txt into the system image, and exposes a control API on port 9090.
#
# HOST REQUIREMENTS:
#   --privileged --device /dev/kvm
#   KVM or nested virt on the host (grep -c vmx /proc/cpuinfo > 0 on Intel,
#   or: [ -e /dev/kvm ] && echo OK)
#   Recommended: bare-metal x86_64, GCP c2/n2, AWS metal, or Hetzner dedicated.
#
# BUILD CONTEXT: repo root (context: ..)
#   dist/whisper.apk
#   whisperd/out/android/x86_64/whisperd
#   aosp/bake_flag.py
#   deploy/victim-runner/entrypoint.sh
#   deploy/victim-runner/runner_api.py
#
# Image size: ~3-4 GB. Build time: 15-30 min (mostly SDK download).

FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    openjdk-17-jre-headless \
    libpulse0 \
    libnss3 \
    libxcomposite1 \
    libxcursor1 \
    libxi6 \
    libxtst6 \
    libgl1 \
    libglu1-mesa \
    libx11-6 \
    libxrandr2 \
    libasound2 \
    socat \
    iptables \
    curl \
    python3 \
    python3-urllib3 \
    unzip \
    e2fsprogs \
    libusb-1.0-0 \
    procps \
    rsync \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

ENV ANDROID_HOME=/opt/android-sdk
ENV PATH="${ANDROID_HOME}/cmdline-tools/latest/bin:${ANDROID_HOME}/platform-tools:${ANDROID_HOME}/emulator:${PATH}"

# Pinned: cmdline-tools 11.0 (commandlinetools-linux-11076708_latest.zip, 2024-12).
ARG CMDLINE_TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
ARG CMDLINE_TOOLS_SHA256="2d2d50857e4eb553af5a6dc3ad507a17adf43d115264b1afc116f95c92e5e258"

RUN mkdir -p "${ANDROID_HOME}/cmdline-tools" && \
    cd /tmp && \
    wget -q -O cmdline-tools.zip "${CMDLINE_TOOLS_URL}" && \
    echo "${CMDLINE_TOOLS_SHA256}  cmdline-tools.zip" | sha256sum -c - && \
    unzip -q cmdline-tools.zip -d /tmp/cmdlinetools && \
    mv /tmp/cmdlinetools/cmdline-tools "${ANDROID_HOME}/cmdline-tools/latest" && \
    rm -rf /tmp/cmdline-tools.zip /tmp/cmdlinetools

# Pin: emulator 35.1.4, platform-tools 35.0.1.
RUN yes | sdkmanager --licenses > /dev/null 2>&1 || true && \
    sdkmanager --install \
        "platform-tools" \
        "emulator" \
        "system-images;android-34;default;x86_64"

RUN test -x "${ANDROID_HOME}/emulator/emulator" || \
    { echo "ERROR: emulator binary not found after install"; exit 1; }

RUN mkdir -p /artifacts

COPY dist/whisper.apk /artifacts/whisper.apk
COPY whisperd/out/android/x86_64/whisperd /artifacts/whisperd
RUN chmod 0755 /artifacts/whisperd

COPY aosp/bake_flag.py /artifacts/bake_flag.py
COPY aosp/bake_image.py /artifacts/bake_image.py
COPY aosp/bake_decoys.py /artifacts/bake_decoys.py
COPY aosp/decoys/system /artifacts/decoys/system
COPY aosp/decoys/whisper_backupd.rc /artifacts/decoys/whisper_backupd.rc
COPY aosp/decoys/whisper_otad.rc /artifacts/decoys/whisper_otad.rc

COPY deploy/victim-runner/entrypoint.sh /entrypoint.sh
COPY deploy/victim-runner/runner_api.py /runner_api.py
RUN chmod 0755 /entrypoint.sh

# Real flag: NEVER hardcoded. Set via WHISPER_REAL_FLAG at container start.
# If unset, a placeholder is used (local testing only).
ENV WHISPER_REAL_FLAG=""
ENV BACKEND_URL="http://backend:8000"
ENV VICTIM_HANDLE="victim"
ENV VICTIM_PHONE="+15550000"
ENV VICTIM_DISPLAY="Whisper Victim"
ENV AVD_NAME="whisper_victim"
ENV RUNNER_HOST="0.0.0.0"
ENV RUNNER_PORT="9090"
# Can be overridden independently if the compose network name differs.
ENV BACKEND_HOST="backend"
ENV BACKEND_PORT="8000"

EXPOSE 9090

ENTRYPOINT ["/entrypoint.sh"]
