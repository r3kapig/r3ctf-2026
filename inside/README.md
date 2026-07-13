# Inside

- **Category:** Crypto
- **Author:**
- **Difficulty:**
- **Wave:**
- **Points:**
- **Solves:**

## Description

Crashed PoLwE — an interactive crypto service built on SageMath. After a
sha256 proof-of-work, players get a menu-driven session (`task.py`) that can
generate a CRS over an elliptic-curve group, sample RLWE statements, and
verify a proof of knowledge via `RLWEProof(st).verify(crs, aux, proof)`. The
intended solve is to forge a valid proof (exploiting a flaw in the CRS/RLWE
proof protocol — "Crashed Proof of LWE"); on a successful verification the
service prints the flag from `$FLAG`. Players connect over TCP to port `9999`.

## Files

- `attachment/` — player handout (the challenge source): `task.py`, `rlwe.py`,
  `sigma.py`.
- `deploy/` — the live service:
  - `src/` — same three Python sources, served inside the container.
  - `Dockerfile` — `sagemath/sagemath:9.6` base, installs `socat` and
    `pycryptodome`, exposes 9999.
  - `docker-entrypoint.sh` — forks a fresh `sage -python task.py` per TCP
    connection via `socat`, then deletes itself.
  - `docker-compose.yml` — compose definition (placeholder `FLAG`, 1 CPU / 1g
    RAM / 128 pids limits).
  - `.dockerignore` — build-context excludes.
- `infra.sh` — build + run script (run from `deploy/`: `cd deploy && ../infra.sh`).

## Deployment

SageMath service over `socat`. Each TCP connection forks a fresh
`sage -python task.py` session (1800s alarm per session). The flag is printed
by `task.py` from `$FLAG` after a valid proof, so the challenge is
**dynamic-flag ready** — the platform injects `FLAG` at runtime; a placeholder
(`r3ctf{to_end_up_where_we_are_meant_to_be}`) is committed in
`docker-compose.yml` for local testing.

```sh
cd deploy && ../infra.sh
# or: cd deploy && docker compose up -d --build
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/inside:latest`
- **Port:** container `9999` (socat), host `9999` (`${INSIDE_PORT:-9999}` in compose)
- **Flag env:** `FLAG` (dynamic, injected at runtime)
- **Resources:** 1 CPU, 1g memory, 128 pids limit
