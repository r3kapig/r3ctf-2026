# P1gROXY

- **Category:** Pwn
- **Author:** uz56764
- **Difficulty:** Hard
- **Wave:** 3
- **Points:** 
- **Solves:** 

## Description

Oink Oink Proxy

Exploiting a 0-day memory leak in zlib (which will likely be 1-day by the time of the
CTF).

## Files

- `attachment/` — player handout: the local-repro source tree (the C++
  `services/proxy` HTTP reverse proxy, the `services/warehousehub` Flask status
  portal, `Dockerfile`, `Makefile`, `deploy/` run scripts, and `docs/`).
- `attachment.zip` — the same handout, zipped (identical to the ret2shell
  platform export).
- `deploy/` — the live container build context.

## Deployment

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/p1groxy:latest`
- **Port:** container `8080` (HTTP), exposed as host `30003` in `infra.sh`
- **Flag:** injected via the `FLAG` environment variable at runtime
