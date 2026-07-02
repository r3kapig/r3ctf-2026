# ret2shell-ext-controller-pod

A generic **per-team bridge pod** template for the ret2shell / k8s-on-demand
platform. The platform spawns one pod per team; the pod is the team's only
entry point and forwards requests to the internal controller with the team's id.

This is the **generic template**. `netshare/ret2shell-ext-controller-pod/` is a
deployed, challenge-specific variant (with its own `pod.yaml`).

## How it works

- The pod reads `RET2SHELL_TEAM_ID` + `CONTROLLER_URL` from the environment.
- It exposes a small Flask UI (`/`) and a few API endpoints
  (`/api/status`, `/api/create`, `/api/delete`).
- Each request is forwarded to the controller at `CONTROLLER_URL/api/<path>` with
  the `X-Team-ID` header set to `RET2SHELL_TEAM_ID`. The team id is never exposed
  to the frontend.

## Files

- `app.py` — the Flask bridge (forwards to the controller).
- `checker.rx` — platform flag-checker template (dynamic-uuid; fill in
  `ENCRYPT_KEY` / `HASH_KEY` / `PREFIX` per challenge).
- `Dockerfile` — `python:3.12-slim`, exposes `5000`.
- `requirements.txt` — `Flask` + `requests`.
- `templates/index.html` — the team dashboard.

## Deploy

The platform (ret2shell / k8s-on-demand) builds + runs one pod per team with env:

```text
RET2SHELL_TEAM_ID=<team id>
CONTROLLER_URL=<internal controller base url>
```

The pod listens on `:5000`.
