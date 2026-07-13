# Whisper

- **Category:** Pwn
- **Author:** lbytes
- **Difficulty:** Medium/Hard
- **Wave:** 3
- **Points:** 
- **Solves:** 

## Description

Slide into their DMs, they won't even open the message.

Whisper is a full-stack Android pwn challenge: a FastAPI messenger backend, an
internal judge, and a pool of victim Android phones (Cuttlefish/AVD on KVM). Each
team leases a victim instance; the victim runs the whisper messenger app and is
signed in to the backend. Players never touch the judge directly — each team gets
its own **auth pod** URL, which proxies lease/release/status and the victim APK
to the judge, and serves the player dashboard. The backend is public and is baked
into the APK:

- backend (public): `http://vm.ctf2026.r3kapig.com:21802`
- judge (pod-only, internal): `http://vm.ctf2026.r3kapig.com:21801`

The real flag lives in a root-only `/flag.txt` inside the victim Android image.
The intended solve is a **zero-click** exploit: deliver a malicious message to the
victim through the messenger (the victim never opens it), achieve heap
exploitation in the app/`whisperd` and escalate to root, then read `/flag.txt`.
Flags are per-team dynamic (`r3ctf{...}`, derived by `checker.rx`); each team's
auth pod pushes its flag to the judge so only that team's victim carries it.

Attachment (player handout, local reproduction stack, ~481 MB):

- [Google Drive](https://drive.google.com/file/d/1fMBIKpfnyogsyCuhXaU04v4IHNB9bwpA/view?usp=sharing)
- [Baidu Pan](https://pan.baidu.com/s/1jjnE50-afruHsXEa6wKPLQ?pwd=R326)

## Files

- `attachment/whisper-local-stack.7z` — player handout: local repro of the FastAPI
  backend plus a single victim runner booting a pre-baked Android image; extract
  and run `./run.sh` inside to develop the exploit locally. Hosted externally
  (too large for the repo); `attachment/whisper-local-stack.txt` is the link
  placeholder.
- `deploy/` — production infrastructure (organizer-only):
  - `deploy/backend/` — FastAPI messenger backend (`Dockerfile`, routers, websockets).
  - `deploy/judge/` — judge web/API, victim pool leasing, APK signing, per-team
    flag store (`pool.py`, `team_flags.py`, `worker.py`).
  - `deploy/aosp/` — Android image-baking tooling (`bake_image.py`, `bake_flag.py`,
    `bake_decoys.py`).
  - `deploy/whisperd/` — the `whisperd` binary baked into the victim image.
  - `deploy/dist/` — `whisper.apk` (the messenger app handed to players).
  - `deploy/deploy/` — compose stack (nginx proxy + backend + judge + N privileged
    victim runners), `run.sh`, `nginx.conf`.
- `auth-pod/` — per-team player-facing pod (Flask app + Dockerfile) that proxies
  lease/status/APK to the judge with the admin token + `team_id`, and pushes the
  team's flag to the judge at boot. See `auth-pod/README.md` for the contract.
- `checker.rx` — platform checker script: per-team dynamic-flag derivation keys
  and the env (`TEAM_ID`, judge/backend URLs, admin token, `FLAG`) handed to each
  team's auth pod.
- `infra.sh` — pointer script only; whisper is a multi-service system with no
  single image to build.

## Deployment

Requires a Linux x86_64 host with KVM (`/dev/kvm`), Docker + Docker Compose v2.

- Local repro (players):

```sh
7zz x attachment/whisper-local-stack.7z
cd whisper-local-stack && ./run.sh
```

- Production stack (organizers):

```sh
cd deploy/deploy && ./run.sh <public-ip> [N]   # N = victim instances, default 2
```

First run downloads the Android SDK image (15–30 min, first victim boot ~10–15
min); later runs are fast. Each victim runner is privileged, needs `/dev/kvm`,
and is capped at 4 CPUs / 6 GB RAM by default. Ports: judge (nginx proxy) `21801`,
backend `21802`. See `deploy/deploy/README.md` for stop/prereq details.

- Per-team auth pods: the platform spawns one `auth-pod` per team with env
  `TEAM_ID` / `WHISPER_JUDGE_URL` / `WHISPER_BACKEND_URL` / `WHISPER_ADMIN_TOKEN`
  / `FLAG` (all supplied by `checker.rx`). On boot the pod pushes the team's flag
  to the judge (`POST /admin/flags`); the judge refuses to lease a victim with no
  pushed flag. Players only ever see their pod URL; the judge stays internal.

Flag handling: **dynamic, per-team**. `WHISPER_REAL_FLAG` is injected at victim
boot and baked into a root-only `/flag.txt` in each Android image; per-team flags
(`r3ctf{...}`) are derived by `checker.rx` and pushed via the auth pods. Only a
placeholder default is committed in `deploy/deploy/run.sh`.
