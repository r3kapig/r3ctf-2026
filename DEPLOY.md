# DEPLOY.md — r3ctf-2026 ops runbook

Remote build / deploy / troubleshooting manual. Condensed agent guide: `AGENTS.md`;
authoritative challenge list: `CHALLENGE.md`. Per-challenge detail lives in each
`<challenge>/README.md`.

---

## 1. Infrastructure

| Item | Value |
|---|---|
| Remote build host | `r3kapig@ops.ctf2026.r3kapig.com` (hostname `r3ctf-ops`) |
| Architecture | `x86_64`, 4 cores, 15Gi RAM, 80G disk, Docker 29.6 + buildx |
| Remote build dir | `~/r3ctf-build/<challenge>/` |
| Registry | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<challenge>:latest` |
| Registry push | Push **directly from the ops host, no `docker login` needed** (IP allowlist) |
| Git repo | `https://github.com/r3kapig/r3ctf-2026.git`, branch `infra` |
| Git auth | `gh auth setup-git` (github.com uses the gh token, non-interactive) |
| SSH | key-based (`BatchMode=yes` works) |

> The remote host has **no `rsync`** — ship files with `tar | ssh tar` (see `AGENTS.md`).

### Helper images (already in the registry, not challenges)

| Image | Purpose |
|---|---|
| `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/sleepy:latest` | Helper image for exposing **multiple ports** on a pod / service (port forwarding / multi-port listening). Source: `docker.io/reverier/sleepy:latest`. |

---

## 2. Remote build playbook

### 2.1 Ship context + build + push

Use the two commands in `AGENTS.md` ("Key commands"): clean-tar the context over ssh
into `~/r3ctf-build/<name>/`, then `docker build` + `docker push` on the ops host.

- If the Dockerfile isn't at the context root (e.g. r3map / polys use
  `deploy/Dockerfile`): `docker build -f deploy/Dockerfile -t <reg>/<name>:latest <context>`.
- Warnings like `tar: Ignoring unknown extended header keyword 'LIBARCHIVE.xattr...'`
  are harmless (GNU tar dropping macOS xattrs). What actually breaks builds is `._*`
  AppleDouble files — the tar command already excludes them; after shipping you can
  confirm with `find ~/r3ctf-build/<name> -name '._*' | wc -l` (expect 0). See §4.1.

### 2.2 Verify

```sh
ssh r3kapig@ops.ctf2026.r3kapig.com \
  'docker buildx imagetools inspect registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest'
```

### 2.3 Resources / concurrency

- The build host has 15Gi RAM — **do not run multiple heavy builds in parallel**
  (this has OOM-rebooted the machine before).
- Heavy builds (SEAL / Nix / PHP source compiles) run serially; for SEAL, change
  `cmake --build build -j` to `-j4` to cap parallelism.
- Lightweight challenges (Python / small C++) can build 2–3 in parallel.

---

## 3. Standard workflow: adding / tidying a challenge

1. **Understand the challenge**: category, flag injection method, whether it needs
   KVM / special privileges, ports.
2. **Lay out the directory**: per `AGENTS.md`, place it at repo root as
   `<challenge>/` with `README.md` + `infra.sh`, container files in `deploy/`,
   player handout in `attachment/`.
3. **Check the flag**: sweep the whole dir with `grep -rEn 'flag\{|r3ctf\{|R3CTF\{'`
   and confirm flag placement matches expectations — dynamic challenges use `$FLAG`
   injection (image bakes only a placeholder); static flags ship with the
   attachment / README.
4. **Remote build + push**: see §2.
5. **Register in `CHALLENGE.md`**: name / image / CPU / memory / special needs.
6. **Commit**: `git add <files> && git commit -m "..." && git push origin infra`.

### Flag injection boilerplate (top of entrypoint; scrub right after parsing)

```sh
if [ -n "$FLAG" ]; then
    INSERT_FLAG="$FLAG"
    export FLAG=no_FLAG
    FLAG=no_FLAG
else
    INSERT_FLAG="flag{TEST_Dynamic_FLAG}"
fi
# then write INSERT_FLAG to /flag or the DB or argv, and start the service
```

---

## 4. Known issues & fixes

### 4.1 macOS `._` AppleDouble files break C/C++ builds

- **Symptom**: `docker build` fails with e.g. `._message.cpp: error: 'Mac' does not name a type`.
- **Cause**: macOS quarantine / provenance xattrs, packed by bsdtar, get restored by
  GNU tar on Linux as real `._<file>` files, which `cmake file(GLOB ...)` then compiles
  as sources.
- **Fix**:
  1. Locally `xattr -cr <dir>` to clear xattrs;
  2. Ship with `COPYFILE_DISABLE=1 tar --exclude='._*' ...`;
  3. Add a `.dockerignore` to the challenge: `**/.git` / `**/.DS_Store` / `**/._*`;
  4. If the remote dir is already polluted: `find <dir> -name '._*' -delete`.

### 4.2 Remote build host OOM reboot

- **Symptom**: SSH suddenly `banner exchange timeout`; after recovery `uptime` shows
  1 minute (the machine rebooted).
- **Cause**: three concurrent builds — SEAL (unbounded `-j`), p1groxy, netshare —
  exhausted the 15Gi RAM.
- **Fix**: run heavy builds serially, cap SEAL at `-j4`; the machine has been
  upgraded, but still don't abuse concurrency.

### 4.3 Dynamic challenges use runtime `$FLAG` injection

- Background: early on, HEuristic's `docker-compose.yml` hardcoded a flag and
  P1gROXY's Dockerfile did `printf > /flag.txt`, baking the flag into the image —
  every team got the same flag / the image carried the flag.
- **Rule**: dynamic challenges always inject `$FLAG` at runtime (entrypoint writes
  `/flag.txt` then scrubs the env); the image bakes only a placeholder. Static
  flags live in the repo with the attachment / README.

### 4.4 whisper deployment

- whisper does not push images; it runs only on the KVM host:
  `cd deploy/deploy && ./run.sh <public-ip> [N]` (N = concurrent device cap).
  Currently deployed on `vm.ctf2026.r3kapig.com` (8 victim devices).
- Building victim images: pulling the debian base from docker.io gets reset by the
  CloudFront CDN in mainland China. Pull the base via the daocloud mirror and tag it
  as the official name: `docker pull docker.m.daocloud.io/library/debian:bookworm-slim
  && docker tag docker.m.daocloud.io/library/debian:bookworm-slim debian:bookworm-slim`
  (same for nginx).
- Its 481M `whisper-local-stack.7z` is hosted on a cloud drive (see `.gitignore` +
  the placeholder `.txt`).

### 4.5 `docker compose config` reports FLAG required

- r3map's compose uses `FLAG: "${FLAG:?FLAG is required}"`, so a bare local
  `docker compose config` fails. **This is expected** (FLAG unset), not a config
  error; verify with `FLAG=test docker compose config`.

---

## 5. whisper per-team auth pod

Hide the judge and give each team a pod as the sole entry point:

```text
player ──► auth pod ──X-Admin-Token + team_id──► judge (internal)
player ──────────────────────────────────────────► backend (public, in APK)
```

- **judge changes** (done):
  - `team_flags.py`: per-team flags **are file-backed by `/data/team_flags.json`**
    (every read/write hits the file, atomic `os.replace`, no in-memory cache).
  - `POST /admin/flags` (admin auth): the auth pod pushes the flag here.
  - `/lease` `/release` `/status`: admin auth + `team_id` from body/query (team
    tokens + `teams.json` removed; the pool indexes directly by `team_id`).
  - `pool._do_assign`: **requires** a pushed flag (`team_flags.get(team_id)`),
    otherwise the lease is refused (`flag_stego.make_flag` removed — the judge no
    longer produces flags).
  - `worker._flag_accepted`: compares directly against the pushed flag
    (flag-sharing / stegano validation is left to the platform checker).
- **auth pod** (`whisper/auth-pod/`):
  - Environment: `TEAM_ID` / `WHISPER_JUDGE_URL` (internal) / `WHISPER_BACKEND_URL`
    (public) / `WHISPER_ADMIN_TOKEN` / optional `FLAG` (defaults to the
    `R3CTF{TEST_FLGA}` placeholder).
  - On startup it pushes the flag; at runtime it proxies
    `lease / release / status / download/whisper.apk` and serves a player
    dashboard (`/`).
- **Deployment**: judge + backend + victim pool are started with
  `deploy/deploy/run.sh` (judge not exposed); the platform (ret.sh /
  k8s-on-demand) starts one auth-pod per team and gives players the pod URL.
- The backend must be publicly exposed (APK connects directly); the judge must be
  internal (pods only).

Details: `whisper/README.md` and `whisper/auth-pod/README.md`.

---

## 6. References

- `reference/creating-ctf-docker/SKILL.md` — source of the conventions this repo
  uses (flag injection, xinetd/socat/direct-listen selection, per-category
  skeletons). Gitignored.
- `reference/r3ctf-2025/` — 40 real 2025 challenges for local reference (gitignored).
- `CHALLENGE.md` — authoritative list of all images / resources / special
  deployment needs.
