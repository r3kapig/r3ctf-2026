# AGENTS.md

Agent guidance for the `r3kapig/r3ctf-2026` repo (`infra` branch): build / deploy
sources for the R3CTF 2026 CTF challenges.

## What this is

- **34 challenges**, each one top-level dir (`<challenge>/`, **flat** — no category
  folders). Per-challenge `README.md` has a fixed format: six metadata bullets +
  Description / Files / Deployment sections; challenge-specific detail lives there.
- Images push to `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<challenge>:latest`.
- Authoritative challenge / image / port / resource list: **`CHALLENGE.md`**.
- Full ops runbook (remote build, troubleshooting, known issues): **`DEPLOY.md`**.
- 5 dirs came from the ret2shell platform export: `r3chat/`, `tap2pwn/`,
  `security-usage-intelligence/`, `survey/`, `sanity-check/`. The last four are
  statement-only (static flag + `checker.rx`). `r3chat/` runs as two images
  `r3chat-{server,bot}:latest`; its build source lives in
  `r3chat/src/` (the 79 MB Windows installer is
  external-only, see `r3chat/attachment/links.txt`).

## Layout

```text
<challenge>/
├── README.md        # six metadata bullets + Description/Files/Deployment
├── infra.sh         # build + run script
├── attachment/      # player handout (large artifacts hosted externally)
└── deploy/          # live container / infra / ops scripts
```

- **Dynamic flag**: entrypoint writes `$FLAG` to the flag location at runtime, then
  scrubs the env (`FLAG=no_FLAG`). Image bakes only a placeholder.
- **Static flag**: ships with the attachment (and may be noted in the README).

## Key commands

Build + push an image (only the **ops host** can push to the registry):

```sh
# 1) ship build context (clean-tar, avoids macOS AppleDouble `._*` files)
COPYFILE_DISABLE=1 tar --exclude='._*' --exclude='.DS_Store' --exclude='.git' \
  -czf - -C <challenge>/<context> . \
  | ssh -o BatchMode=yes r3kapig@ops.ctf2026.r3kapig.com \
    'rm -rf ~/r3ctf-build/<name> && mkdir -p ~/r3ctf-build/<name> && tar xzf - -C ~/r3ctf-build/<name>'

# 2) build + push on ops
ssh r3kapig@ops.ctf2026.r3kapig.com \
  'cd ~/r3ctf-build/<name> \
   && docker build -t registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest . \
   && docker push registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest'
```

If the Dockerfile isn't at the context root:
`docker build -f deploy/Dockerfile -t <reg>/<name>:latest <context>`.

## Boundaries

- **Only ops pushes to the registry.** The VM host (`vm.ctf2026.r3kapig.com`)
  builds/runs whisper victims locally; use `rsync` to the VM, `tar | ssh tar` to ops.
- **File size:** `>100MB` is rejected (GH001), `>50MB` warns. Compress to 7z, or
  host externally + a `.txt` placeholder. Scan with `find . -type f -size +50M`.
- **No parallel heavy builds** on the ops host (15Gi RAM). SEAL / Nix / PHP-source
  compiles are heavy — run serially.
- **macOS tar:** always `COPYFILE_DISABLE=1` + `--exclude='._*'` (AppleDouble files
  break C/C++ builds).
- `reference/` is gitignored (1.2G of 2025 reference material; not part of the repo).

## Conventions

- Branch `infra`, set-upstream to `origin/infra`. Commit + `git push origin infra`.
- After adding / renaming / re-imaging a challenge: update **`CHALLENGE.md`**
  (image, CPU, memory, status) and, if the workflow changed, this file.
- Flag format: `r3ctf{...}` (lowercase) for dynamic flags; `checker.rx` /
  `flag.param.md` hold per-team derivation keys.

## Pointers

- `CHALLENGE.md` — image / CPU / memory / port / status per challenge.
- `DEPLOY.md` — remote build playbook + known issues / fixes.
- `whisper/README.md`, `whisper/auth-pod/README.md` — whisper stack + auth pod.
- `babycom/OPS.md`, `someday/OPS.md` — VM-hosted challenge runbooks.
- `reference/creating-ctf-docker/SKILL.md` — the convention source (gitignored).
