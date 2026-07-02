#!/bin/sh
# trustedhash is a Nix-based TPM challenge (player VM + operator portal).
# The per-team portal image is already built/pushed as .../trustedhash:latest.
# Run one portal per team (needs --privileged + KVM + per-team FLAG):
#   docker run --rm -d --privileged --device /dev/kvm -e FLAG=<per-team> \
#     -p <host-ssh>:2222 -p <host-agent>:31337 \
#     registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/trustedhash:latest
# See operator/README.md for full flags.
set -e
echo "trustedhash: run per-team portal from the pushed image; see operator/README.md."
