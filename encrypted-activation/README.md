# Encrypted Activation

- **Author:** SSGSS
- **Submissions:** 118
- **Solves:** 12

## Description

The remote server uses a fixed key. The evaluation keys are provided in the attachments.

An FHE (fully homomorphic encryption) challenge. The server encrypts base-4
activation digits (5 digits = one 10-bit value) and asks the player to evaluate
a published 1024-entry lookup table (`lut`) on the encrypted inputs across 16
rounds, returning the encrypted output symbols each round. Solve all rounds to
get the flag. The heavy homomorphic evaluation happens on the player side using
the provided keys; the server only encrypts the inputs and decrypts/verifies the
answers (120s per-connection timeout).

## Files

- `attachment/` — player handout: `task.py` (the stdin/stdout service),
  `fhe_core.py` (FHE scheme), `lut` (1024-entry activation table),
  `setup/client.bin` (client/evaluation key material), and a placeholder
  `secret.py` for local runs.
- `deploy/` — live container: `Dockerfile` (build context is the challenge
  root, `COPY`s from `attachment/`), `docker-compose.yml`, `wrap.py` (TCP
  wrapper), and the real env-based `secret.py`.
- `infra.sh` — build + run script (builds the image from the challenge root,
  runs it with a test `FLAG`, 1 CPU / 512Mi RAM, port 1336).

## Deployment

`task.py` is a stdin/stdout service; `deploy/wrap.py` binds TCP port **1336** and
bridges each connection to a fresh `task.py` subprocess. No `socat` is needed,
so the image is just `python:3.12-slim` plus the challenge files. The flag is
dynamic: injected at runtime via the `FLAG` environment variable, which
`deploy/secret.py` reads (`attachment/secret.py` is only a placeholder for local
reproduction).

Image: `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/encrypted-activation:latest`

```sh
# build (context = challenge root; the Dockerfile COPYs from attachment/)
docker build -f deploy/Dockerfile -t registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/encrypted-activation:latest .
# local run:
cd deploy && FLAG='r3ctf{test}' docker compose up -d
# or via the helper script:
./infra.sh
```

Runtime needs no special devices (pure-CPU Python crypto); 1 CPU / 512Mi RAM as
per `infra.sh`. Per-connection compute is modest.
