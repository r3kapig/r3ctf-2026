# cuttlefish-runner -- privileged container that boots and manages Cuttlefish victim VMs.
#
# HOST REQUIREMENTS:
#   - Linux host with KVM support: /dev/kvm must be present and accessible.
#   - Nested virtualization enabled (required for cloud VMs; bare-metal has it natively).
#     Verify: [ -e /dev/kvm ] && echo "KVM OK" || echo "NO KVM -- cannot run"
#   - The container is run with --privileged and --device /dev/kvm.
#   - Recommended host: bare-metal x86_64, or a cloud instance with nested-virt
#     (e.g., GCP c2/n2 with "Enable vTPM" off, AWS metal instances, or Hetzner
#     dedicated with nested virt).
#
# This Dockerfile stubs the runner. Full implementation requires the aosp-engineer
# to provide the Cuttlefish image assembly artifacts and boot scripts.
# The runner exposes a minimal HTTP API (port 9090) consumed by judge-worker:
#   POST /reset  -- reset the victim to a clean snapshot, return 200 when ready
#   GET  /health -- liveness probe
#
# For local development without KVM, the cuttlefish-runner service is optional
# (see the "no-kvm" compose profile). The judge-worker falls back to goldfish AVD
# mode (direct adb to emulator-5554) when CF_RUNNER_URL is not set.

FROM ubuntu:22.04

# Install KVM tools + Python for the control API
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip adb curl wget unzip \
    qemu-kvm libvirt-daemon-system \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --no-cache-dir flask requests

WORKDIR /runner

# Copy control scripts from the repo's aosp/ directory
COPY aosp/ /runner/aosp/
COPY deploy/cuttlefish-runner/runner_api.py /runner/runner_api.py

ENV WHISPER_REAL_FLAG=""
ENV WHISPER_APK_PATH=/runner/dist/whisper.apk
ENV WHISPER_WHISPERD_PATH=/runner/whisperd/out/android/x86_64/whisperd
ENV RUNNER_HOST=0.0.0.0
ENV RUNNER_PORT=9090

EXPOSE 9090

# Verify KVM at startup; fail loudly if missing
CMD ["sh", "-c", "[ -e /dev/kvm ] || { echo 'ERROR: /dev/kvm not found. This container requires a KVM-capable host.'; exit 1; }; python3 runner_api.py"]
