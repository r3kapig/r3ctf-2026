# whisper auth pod

Per-team pod that sits between the player and the (internal) whisper judge. The
judge is **not** exposed to players; each team talks only to its own pod.

```
player ──► auth pod ──X-Admin-Token + team_id──► judge (internal)
player ──────────────────────────────────────────► backend (public, in APK)
```

## What it does

- Proxies `lease / release / status / download/whisper.apk` to the judge using the
  judge admin token + the team's `TEAM_ID`.
- On boot, and again before each lease, pushes the team's flag to the judge
  (`POST /admin/flags`) so the victim uses the platform's flag.
- Serves the player dashboard (replica of the judge UI) on `/`.

## Env

| Var | Required | Description |
|---|---|---|
| `TEAM_ID` | yes | numeric team id |
| `WHISPER_JUDGE_URL` | yes | judge URL (pod-only), e.g. `http://judge:8080` |
| `WHISPER_BACKEND_URL` | yes | public messenger backend URL (baked into the APK) |
| `WHISPER_ADMIN_TOKEN` | yes | judge admin token |
| `FLAG` | optional | flag to push to the judge (defaults to a test placeholder) |

## Build / run

```sh
docker build -t whisper-auth-pod .
docker run --rm -p 5000:5000 \
  -e TEAM_ID=1 \
  -e WHISPER_JUDGE_URL=http://vm.ctf2026.r3kapig.com:21801 \
  -e WHISPER_BACKEND_URL=http://vm.ctf2026.r3kapig.com:21802 \
  -e WHISPER_ADMIN_TOKEN=<admin> -e FLAG='R3CTF{...}' \
  whisper-auth-pod
```

Production endpoints:

- judge (pod-only): `http://vm.ctf2026.r3kapig.com:21801`
- backend (public, baked into APK): `http://vm.ctf2026.r3kapig.com:21802`

The platform spawns one pod per team with the per-team `TEAM_ID` / `FLAG`, and
hands the player the pod URL. `WHISPER_JUDGE_URL` / `WHISPER_BACKEND_URL` /
`WHISPER_ADMIN_TOKEN` are shared across all team pods.
