# Blinky R3CTF challenge server.
#
# Runtime = python3 (stdlib server) + the mips64el binutils, because the kernel
# image is (re)assembled at container start to bake in the per-instance dynamic
# flag (see deploy/entrypoint.sh). The PAC key is randomised per submission by
# server.py, so every run authenticates a different tag.
#
# Build context is the challenge root:
#   docker build -f deploy/Dockerfile -t <reg>/blinky:latest .
#
# Base image note: SOC_run_sim is a PREBUILT x86-64 binary linked against the host
# glibc/libstdc++ it was compiled on (currently GLIBC_2.38 / GLIBCXX_3.4.32). The
# base image must be new enough or the sim won't start and every submission returns
# "(no output)". ubuntu:24.04 (glibc 2.39, GCC 14) satisfies it; debian:bookworm is
# TOO OLD. If you rebuild SOC_run_sim on a newer host, bump this accordingly (the
# entrypoint smoke-test will otherwise fail fast).
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        binutils-mips64el-linux-gnuabi64 \
        libstdc++6 \
        ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Server code + the 0dMIPS pieces it needs to (re)build the kernel image:
#   server.py, SOC_run_sim, kernel.s, script.ld, build_kernel.sh
COPY deploy/server/ /app/server/
COPY deploy/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh /app/server/build_kernel.sh /app/server/SOC_run_sim

# Bake a PLACEHOLDER kernel image at build time (the real flag is injected at
# container start by the entrypoint). This also fails the build early if the
# toolchain / sources are wrong.
RUN FLAG='R3CTF{TEST_Dynamic_FLAG}' \
        OUT=/app/server/kernel_template.mem \
        /app/server/build_kernel.sh

# Drop privileges.
RUN useradd -m -u 10001 ctf && chown -R ctf:ctf /app
USER ctf

ENV HOST=0.0.0.0 PORT=8080
EXPOSE 8080
ENTRYPOINT ["/app/entrypoint.sh"]
