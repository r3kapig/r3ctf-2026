# Encrypted Activation

- **Category:** Crypto
- **Author:**
- **Difficulty:**
- **Wave:**
- **Points:**
- **Solves:**

## Description

The remote server uses a fixed key. The evaluation keys are provided in the attachments.

An FHE (fully homomorphic encryption) challenge. The server encrypts base-4
activation digits and asks the player to evaluate a published 10-bit lookup table
on the encrypted inputs across 16 rounds. Solve all rounds to get the flag.

## Files

- `attachment/` — player handout: `task.py`, `fhe_core.py`, `lut`,
  `setup/client.bin`, and a placeholder `secret.py` for local runs.
- `deploy/` — live container: `Dockerfile`, `docker-compose.yml`, `wrap.py` (TCP
  wrapper), and the real env-based `secret.py`.

## Deployment

`task.py` is a stdin/stdout service; `deploy/wrap.py` binds TCP port **1336** and
bridges each connection to a fresh `task.py` subprocess (120s per-connection
timeout inside `task.py`). No `socat` is needed, so the image is just
`python:3.12-slim` plus the challenge files. The flag is injected at runtime
via the `FLAG` environment variable — `deploy/secret.py` reads it; the
`attachment/secret.py` is only a placeholder for local reproduction.

Build context is the challenge root (the Dockerfile `COPY`s from `attachment/`):

```sh
docker build -f deploy/Dockerfile -t registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/encrypted-activation:latest .
# local run:
cd deploy && FLAG='r3ctf{test}' docker compose up -d
```

Runtime needs no special devices (pure-CPU Python crypto). Per-connection compute
is modest (the heavy homomorphic evaluation happens on the player side).
