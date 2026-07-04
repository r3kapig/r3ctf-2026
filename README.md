# R3CTF 2026

Source code and deployment material for the R3CTF 2026 challenges.

This is the `infra` branch, holding the challenge build / deploy sources.

- See [`CHALLENGE.md`](./CHALLENGE.md) for the full challenge list with CPU / memory
  limits, image names, ports, and deploy notes.
- See [`DEPLOY.md`](./DEPLOY.md) for the ops runbook (remote build → push →
  deploy → troubleshooting).
- See [`AGENTS.md`](./AGENTS.md) for concise agent guidance + conventions.

## Layout

Challenges live **flat at the repo root** (no category folders). Each follows the
r3ctf convention:

```text
<challenge>/
├── README.md
├── infra.sh
├── attachment/   # public handout (large artifacts are hosted externally)
└── deploy/       # live container / infra / ops scripts
```

VM-hosted challenges (e.g. `whisper`, `virtisol`, `winkernel`) keep only their
ops scripts in `deploy/`; the guest images and per-instance configs live on the
VM host, not in git.

## Challenges

Images built and pushed to
`registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest`:

`ezvpn`, `HEuristic`, `rECp1cG`, `P1gROXY`, `netshare`, `trustedhash`,
`r3map`, `TsukisRhythmGame`, `definitely-not-a-web-chal`, `r3ticket`, `z3kapig`,
`polys`.

No image (static attachment / local run / VM-host deployment):

`whisper`, `pewpew`, `Time Capsule`, `teRRibleRing`, `lift`, `virtisol`,
`winkernel`.

Again, see [`CHALLENGE.md`](./CHALLENGE.md) for details.

## Large artifacts

Files over GitHub's 100MB limit are **not** stored in the repo (see `.gitignore`):

- `whisper/attachment/whisper-local-stack.7z` (~481MB) — hosted externally; the
  placeholder `whisper-local-stack.txt` stays in git.
- `Time Capsule/attachment/` (uncompressed dir) — only the packed
  `attachment.7z` (~58MB) is committed.

They are distributed via the contest platform / object storage.
