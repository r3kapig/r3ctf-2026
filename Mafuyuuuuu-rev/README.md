# Mafuyuuuuu-rev

- **Category:** 
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

Take a short break and listen to some music. But can you find the true feelings Mafuyu has hidden behind these cold melodies?

Note: For this version, you need the flag from the previous challenge. Convert it to lowercase, then calculate its SHA-256 hash. The resulting hex digest is the attachment password.

Example:
- r3ctf{T3ST_FL@G} -> test_flag -> sha256(...)

If you already got the flag from `mafuyuuuuu` but the password doesn’t work, please open a ticket!

## Files

- `attachment/to-player.zip` — player handout (the challenge source tree).
- `deploy/` — the live three-container service: `nginx/`, `frontend/`,
  `Dockerfile.backend`, `deploy/` (backend build + flag), `docker-compose.yml`,
  `k8s.yaml`.

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

Images: `mafuyuuuuu-rev-{nginx,frontend,backend}:latest`. The pod exposes port
`8089` (the `k8s.yaml` Service uses NodePort `30089`). The flag is mounted into
the backend at `/flag` from the `mafuyuuuuu-flag` ConfigMap — replace it with
the real/dynamic flag for the event. The local test flag is `deploy/deploy/flag`.

## Solve

```sh
python3 solve/solve.py http://127.0.0.1:8089
```
