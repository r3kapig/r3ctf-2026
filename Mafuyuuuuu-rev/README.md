# Mafuyuuuuu-rev

Mafuyuuuuu is a Project SEKAI themed .NET web challenge. The public service is a three-container stack:

- `nginx`: public reverse proxy on port `8089`
- `frontend`: Vite/Tailwind UI
- `backend`: ASP.NET Core API, `/flag`, and `/readflag`

## Deploy

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

## Player Attachment

The player package is:

```text
attachment/to-player.zip
```

## Solve

```sh
python3 solve/solve.py http://127.0.0.1:8089
```
