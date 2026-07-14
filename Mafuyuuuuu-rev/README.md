# Mafuyuuuuu-rev

- **Author:** yuu_2802
- **Submissions:** 22
- **Solves:** 19

## Description

Take a short break and listen to some music. But can you find the true feelings Mafuyu has hidden behind these cold melodies?

This is the hardened "rev" version of `mafuyuuuuu`: a three-container web service — a Vite/React frontend, a .NET 8 backend (`PaperTrailDesk.dll`), and an nginx reverse proxy. The flag lives at `/flag` inside the backend container, readable only through a setuid `/readflag` binary, so players must reverse the backend and find a way to make it read the flag.

Note: For this version, you need the flag from the previous challenge. Convert it to lowercase, then calculate its SHA-256 hash. The resulting hex digest is the attachment password.

Example:

- `r3ctf{T3ST_FL@G}` -> `test_flag` -> `sha256(...)`

If you already got the flag from `mafuyuuuuu` but the password doesn't work, please open a ticket!

## Files

- `attachment/to-player.zip` — player handout (the challenge source tree), password-protected as described above.
- `deploy/` — the live three-container service:
  - `deploy/deploy/` — backend artifacts: `PaperTrailDesk.dll`, `entrypoint.sh` (dynamic-flag writer), `readflag.c` (setuid flag reader), `supervisord.conf`, local test `flag`.
  - `deploy/frontend/` — Vite/React frontend with its own `Dockerfile` (port 4173).
  - `deploy/nginx/` — nginx reverse proxy (`nginx.conf` for compose, `nginx.pod.conf` baked for the pod).
  - `deploy/Dockerfile.backend` — .NET 8 backend image build (port 8080).
  - `deploy/docker-compose.yml` — local three-service compose stack.
  - `deploy/k8s.yaml` — production single-pod, three-container manifest.
- `infra.sh` — build + run the compose stack (`docker compose up -d --build` in `deploy/`).
- `solve/solve.py` — reference solver: `python3 solve/solve.py http://127.0.0.1:8089`.

## Deployment

Local dev (docker compose, nginx proxies via service names):

```sh
./infra.sh
```

The service listens on `http://127.0.0.1:8089/`.

Production (single pod, three containers — nginx proxies to `127.0.0.1`):

```sh
kubectl apply -f deploy/k8s.yaml
```

Images: `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/mafuyuuuuu-rev-{nginx,frontend,backend}:latest`. The pod exposes port `8089` via a NodePort Service (`30090`).

Dynamic flag: the platform injects the per-team flag via the `$FLAG` env var (also `$GZCTF_FLAG` / `$DASFLAG`); the backend `entrypoint.sh` writes it to `/flag` (mode 0400, root-owned), scrubs the env (`FLAG=no_FLAG`), and starts the backend as an unprivileged user under supervisord. The image bakes only the placeholder `r3ctf{test_flag_replace_me}` (also used as `deploy/deploy/flag` for local testing).
