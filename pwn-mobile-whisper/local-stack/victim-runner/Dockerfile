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
    curl \
    python3 \
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

ARG CMDLINE_TOOLS_URL="https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip"
ARG CMDLINE_TOOLS_SHA256="2d2d50857e4eb553af5a6dc3ad507a17adf43d115264b1afc116f95c92e5e258"

RUN mkdir -p "${ANDROID_HOME}/cmdline-tools" && \
    cd /tmp && \
    wget -q -O cmdline-tools.zip "${CMDLINE_TOOLS_URL}" && \
    echo "${CMDLINE_TOOLS_SHA256}  cmdline-tools.zip" | sha256sum -c - && \
    unzip -q cmdline-tools.zip -d /tmp/cmdlinetools && \
    mv /tmp/cmdlinetools/cmdline-tools "${ANDROID_HOME}/cmdline-tools/latest" && \
    rm -rf /tmp/cmdline-tools.zip /tmp/cmdlinetools

RUN yes | sdkmanager --licenses > /dev/null 2>&1 || true && \
    sdkmanager --install \
        "platform-tools" \
        "emulator" \
        "system-images;android-34;default;x86_64"

RUN test -x "${ANDROID_HOME}/emulator/emulator" || \
    { echo "ERROR: emulator binary not found after install"; exit 1; }

RUN mkdir -p /artifacts

COPY whisper.apk /artifacts/whisper.apk
COPY entrypoint.sh /entrypoint.sh
COPY runner_api.py /runner_api.py
RUN chmod 0755 /entrypoint.sh

ENV BACKEND_URL="http://backend:8000"
ENV BACKEND_HOST="backend"
ENV BACKEND_PORT="8000"
ENV VICTIM_HANDLE="victim"
ENV VICTIM_PHONE="+15550000"
ENV VICTIM_DISPLAY="Whisper Victim"
ENV AVD_NAME="whisper_victim"
ENV RUNNER_HOST="0.0.0.0"
ENV RUNNER_PORT="9090"
ENV SYSTEM_IMG_PATH="/mnt/system.img"

EXPOSE 9090

ENTRYPOINT ["/entrypoint.sh"]
