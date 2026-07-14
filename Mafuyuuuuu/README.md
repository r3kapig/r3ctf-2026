# Mafuyuuuuu

- **Author:** yuu_2802
- **Submissions:** 42
- **Solves:** 26

## Description

Take a short break and listen to some music. But can you find the true feelings Mafuyu has hidden behind these cold melodies?

A web challenge: a three-container service (nginx reverse proxy → Vite/Node frontend + .NET 8 backend `PaperTrailDesk`). The flag lives at `/flag` inside the backend container, readable only by root; a setuid `/readflag` binary can print it. The intended solve is achieving code execution in the backend (see `solve/solve.py`, which builds shellcode to run `/readflag` and exfiltrate the flag via `/app/exports/`).

## Files

- `attachment/to-player.zip` — player handout (the challenge source tree).
- `infra.sh` — local build + run: `docker compose up -d --build` in `deploy/`.
- `deploy/` — the live service:
  - `deploy/docker-compose.yml` — local dev stack (nginx proxies via service names).
  - `deploy/Dockerfile.backend` — .NET 8 backend image; builds the setuid `/readflag`, bakes `/flag` placeholder, locks down `/app`.
  - `deploy/deploy/` — backend payload: `PaperTrailDesk.dll`, `entrypoint.sh` (dynamic flag), `readflag.c`, `supervisord.conf`, test `flag`.
  - `deploy/frontend/` — Vite frontend image (port 4173).
  - `deploy/nginx/` — nginx image + configs (`nginx.conf` for compose, `nginx.pod.conf` for the pod).
  - `deploy/k8s.yaml` — production: single pod, three containers, ConfigMap nginx conf, NodePort Service.
- `solve/solve.py` — reference exploit (`python3 solve/solve.py http://127.0.0.1:8089`).

## Deployment

Local dev:

```sh
./infra.sh
```

The service listens on `http://127.0.0.1:8089/`.

Production (single pod, three containers — nginx proxies to `127.0.0.1`):

```sh
kubectl apply -f deploy/k8s.yaml
```

Images: `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/mafuyuuuuu-{nginx,frontend,backend}:latest`. The pod exposes port `8089` via NodePort `30089`.

Dynamic flag: the platform injects `$FLAG` (also accepts `$DASFLAG` / `$GZCTF_FLAG`) into the backend container; `deploy/deploy/entrypoint.sh` writes it to `/flag` (root-only, read via the setuid `/readflag`), then scrubs the env before starting the backend. The baked placeholder / local test flag is `r3ctf{test_flag_replace_me}` (`deploy/deploy/flag`).

Resources (from `k8s.yaml`): backend 250m/256Mi → 1/1Gi, frontend 100m/128Mi → 500m/512Mi, nginx 50m/32Mi → 200m/128Mi.
