# HEuristic

- **Author:** dengfeng
- **Submissions:** 100
- **Solves:** 83

## Description

HE is HEuristic. A heuristic homomorphic-encryption service built on Microsoft SEAL
(CKKS). Recover the secret scale `delta` using a limited number of encrypt/decrypt
oracle rounds, then submit `delta mod q` to get the flag. You get only 3 rounds; the
decrypt oracle adds per-coefficient noise and masks high indices. The flag is printed
by the service only when the correct `delta` is submitted.

## Files

- `attachment/` — player handout: `server.cc`, `CMakeLists.txt`, and `run.sh`
  (build script; clones Microsoft SEAL and builds `he_server` locally).
- `deploy/` — live container build: `Dockerfile` (multi-stage, compiles `he_server`
  against the vendored SEAL copy in `src/thirdparty/seal`), `src/` (server source +
  vendored SEAL), `service/docker-entrypoint.sh` (socat wrapper), and
  `docker/docker-compose.yml` (local test compose).
- `infra.sh` — build + run script; run from inside `deploy/`.

## Deployment

Docker image `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/heuristic:latest`.
The container runs `he_server` behind `socat` on port 9999, published as host port
30002 with `--cpus 0.1 --memory 256m`.

The flag is dynamic: injected via the `FLAG` environment variable at runtime and read
by the service with `getenv("FLAG")`; it is printed only when a player submits the
correct `delta`.

```sh
cd deploy && ../infra.sh
```

Building SEAL from source is heavy — build serially on the ops host (see DEPLOY.md).
