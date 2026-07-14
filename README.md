# R3CTF 2026

Challenge build / deploy sources for R3CTF 2026 (`master` branch).

## Layout

Challenges live **flat at the repo root** (no category folders), 34 total. Each
follows the convention:

```text
<challenge>/
├── README.md      # metadata + description
├── infra.sh       # build + run script
├── attachment/    # player handout (large artifacts hosted externally)
└── deploy/        # live container / infra / ops scripts
```

VM-hosted challenges (e.g. `whisper`, `babycom`, `someday`) keep only ops scripts
in `deploy/`; guest images and per-instance configs live on the VM host, not in git.
Shared GKE ops helpers live in [`ops/`](./ops/README.md).

## Docs

- [`CHALLENGE.md`](./CHALLENGE.md) — authoritative challenge / image / port /
  resource list.
- [`RANK.md`](./RANK.md) — final top-50 scoreboard (hidden/banned excluded)
  with per-challenge solve matrix.
- [`DEPLOY.md`](./DEPLOY.md) — ops runbook (remote build → push → deploy →
  troubleshooting).
- [`AGENTS.md`](./AGENTS.md) — agent guidance + conventions.
- `<challenge>/README.md` — per-challenge detail; `babycom/OPS.md` /
  `someday/OPS.md` — VM-hosted challenge runbooks.

## Conventions

Images push to `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest`
(ops host only). Dynamic flags are injected via `$FLAG` at runtime; static flags
ship with the attachment. Files >100MB are rejected by GitHub, so large artifacts
are compressed to 7z or hosted externally with a `.txt` placeholder in git (see
`.gitignore`).
