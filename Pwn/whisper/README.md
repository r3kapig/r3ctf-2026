# whisper

- **Category:** Pwn
- **Author:** 
- **Points:** 
- **Solves:** 

## Description

A 0-click Android exploit chain delivered through a messaging app. Craft a malicious
`.rcard` attachment, send it to a victim over the `whisper` messenger, and trigger a
heap-to-root exploit in the privileged native `whisperd` daemon inside
`com.whisper.app` to read the root-only `/flag.txt`.

## Architecture

- `attachment/whisper-local-stack.7z` — the player handout: a local reproduction of
  the FastAPI messenger backend plus a single victim runner that boots a pre-baked
  Android image. Extract it and run `./run.sh` inside to develop the exploit locally.
- `deploy/` — production infrastructure: the judge, the per-team victim pool, the
  AOSP image-baking tooling (`aosp/`), the `whisperd` binary, and the compose stack
  (nginx + backend + judge + N victim runners) under `deploy/deploy/`.
- `auth-pod/` — **Model B** per-team pod: sits between the player and the judge,
  authenticates the player (`POD_TOKEN`), proxies lease/status/APK to the judge, and
  pushes a platform flag to the judge at boot. The judge is not exposed to players.

## Deployment

The real flag is injected at victim-boot time via `WHISPER_REAL_FLAG` and baked into
a root-only `/flag.txt` inside each Android image; per-team dynamic flags are derived
by the judge. Only placeholders are committed.

- Local repro (players): extract `attachment/whisper-local-stack.7z`, then
  `cd whisper-local-stack && ./run.sh`.
- Production stack (organizers): `cd deploy/deploy && ./run.sh`.

### Model B (per-team auth pod)

For platform-managed per-team flags + a single player-facing entry per team:

1. Run the judge + backend + victim pool: `cd deploy/deploy && ./run.sh <public-ip> [N]`.
   The judge is **internal** (not exposed to players).
2. The platform spawns one `auth-pod` per team with env `TEAM_ID` / `POD_TOKEN`
   (random) / `WHISPER_JUDGE_URL` (internal) / `WHISPER_BACKEND_URL` (public) /
   `WHISPER_ADMIN_TOKEN` / optional `FLAG`.
3. On boot the pod pushes the platform flag to the judge (`POST /admin/flags`); the
   judge requires it for that team's victim (`pool._do_assign` refuses a lease with
   no pushed flag).
4. Players reach only their pod (URL + `POD_TOKEN`); the pod proxies lease/status/APK
   to the judge (admin token + `team_id`). The backend stays public (the APK connects
   to it directly).

See `auth-pod/README.md` for the pod contract.

## Files

- `attachment/whisper-local-stack.7z` — player handout (local repro), 7z-compressed.
- `deploy/` — production infra (organizer-only).
- `auth-pod/` — Model B per-team auth pod (player-facing proxy to the judge).
