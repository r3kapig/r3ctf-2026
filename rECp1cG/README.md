# rECp1cG

- **Author:** deebato
- **Submissions:** 19
- **Solves:** 3

## Description

Quiet steps, old notes: https://eprint.iacr.org/2007/099.pdf — ECLCG / ECHNP.

Each TCP connection generates a fresh 1024-bit prime `p` and a random elliptic
curve `y² = x³ + a·x + b (mod p)`, then publishes `p, a, b, Delta (= 2^451)`,
a generator point `G`, and `k = 21` "states": the x-coordinates of consecutive
multiples `P_i = i·G`, each perturbed by a random error of up to `2^451` bits.
The player must recover the exact x-coordinate of `P0` (an Elliptic-Curve
Hidden Number Problem / EC LCG state recovery, 888 s per-connection timeout).
On a correct answer the service reveals `key_tag` and `ct`: the flag XORed
with a SHA-256 keystream derived from the curve parameters — recovering `P0.x`
lets the player recompute the key and decrypt the flag.

## Files

- `attachment/challenge.py` — player handout (the challenge script).
- `deploy/` — live TCP service build context:
  - `challenge.py` — per-connection challenge generator and answer verifier.
  - `secret.py` — reads the flag from the `FLAG` environment variable
    (placeholder `r3ctf{test_placeholder}` in the repo).
  - `Dockerfile` — Ubuntu 24.04 + python3 + `socat`, runs as non-root user,
    serves `python -u challenge.py` on container port 9999.
  - `docker-compose.yml`, `.env.example`, `.dockerignore` — local smoke-test
    deployment (hardened: read-only rootfs, tmpfs `/tmp`, `no-new-privileges`,
    `pids_limit`).
  - `DEPLOYMENT.md` — full remote-deployment notes (parameters, compose usage,
    base-image alternatives).
- `infra.sh` — builds the image and runs the container on the host.

## Deployment

Dynamic flag: `FLAG` env var is injected at runtime and read by `secret.py`;
only a placeholder ships in the image.

```sh
cd deploy && ../infra.sh
```

`infra.sh` builds `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/recp1cg:latest`
and runs it with host port `30005` → container port `9999`, limited to
`--cpus 0.1 --memory 128m`. Local testing alternative:

```sh
cd deploy && FLAG='r3ctf{test_placeholder}' docker compose up --build -d
nc 127.0.0.1 9999
```
