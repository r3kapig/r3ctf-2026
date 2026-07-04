# inside

- **Category:** Crypto
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

An RLWE + sigma-protocol proof-of-knowledge challenge built on SageMath. Players
interact with a remote service, generate a CRS and an RLWE statement, then produce
a valid proof of knowledge to recover the flag.

## Files

- `attachment/{task.py, rlwe.py, sigma.py}` — player handout (the challenge source).
- `deploy/` — the live service: `src/`, `Dockerfile`, `docker-entrypoint.sh`,
  `docker-compose.yml`.

## Deployment

SageMath service over `socat`. Each TCP connection forks a fresh `sage -python
task.py` session. The flag is printed by `task.py` from `$FLAG` after a valid
proof, so the challenge is **dynamic-flag ready** — the platform injects `FLAG`
at runtime; a placeholder is committed in `docker-compose.yml` for local testing.

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/inside:latest`
- **Port:** container `9999` (socat), host `9999`
- **Flag env:** `FLAG`
