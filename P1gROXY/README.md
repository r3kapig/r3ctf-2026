# P1gROXY

- **Category:** Pwn
- **Author:** uz56764
- **Difficulty:** Hard
- **Wave:** 3
- **Points:** 
- **Solves:** 

## Description

Oink Oink Proxy — exploiting a 0-day memory leak in zlib (which will likely be
1-day by the time of the CTF).

The deployment runs two services behind a single public HTTP port:

- `services/proxy` — P1gROXY, a C++ HTTP/1.1 reverse proxy built against a
  private, vendored zlib (`services/proxy/vendor/zlib`). It owns all edge HTTP
  behavior: connection handling, hop-by-hop header policy, content-coding
  normalization, upstream forwarding, response parsing/adaptation, HTML URL
  normalization, caching metadata, and security headers.
- `services/warehousehub` — WarehouseHub, a small internal Flask status portal
  bound to localhost, serving read-only operational pages and health JSON for
  the proxy to publish.

The flag lives at `/flag.txt` (world-readable, owned by root) inside the
container; the stack itself runs as the unprivileged `warehousehub` user.
Players are expected to attack the proxy's zlib handling to leak memory and
recover the flag over HTTP.

## Files

- `attachment/` — player handout: the local-repro source tree (`services/proxy`
  C++ reverse proxy, `services/warehousehub` Flask portal, `Dockerfile`,
  `Makefile`, `deploy/` run scripts and env files, `docs/`).
- `attachment.zip` — the same handout, zipped (identical to the ret2shell
  platform export).
- `deploy/` — the live container build context: multi-stage `Dockerfile`,
  `service/docker-entrypoint.sh`, `deploy/run-container.sh`, service sources,
  `docs/`, and `docker/docker-compose.yml` for local testing.
- `infra.sh` — build + run script; run it from inside `deploy/`.

## Deployment

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/p1groxy:latest`
- **Port:** container `8080` (HTTP), exposed as host `30003` in `infra.sh`
- **Flag:** dynamic — injected via the `FLAG` environment variable at runtime.
  `service/docker-entrypoint.sh` writes it to `/flag.txt`, scrubs the env
  (`FLAG=no_FLAG`), then drops privileges to `warehousehub` and starts the
  proxy + portal stack. The image bakes only `r3ctf{placeholder}`.
- **Resources:** `infra.sh` limits the container to `--cpus 0.1 --memory 128m`.
