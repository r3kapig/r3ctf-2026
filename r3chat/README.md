# r3chat

- **Author:** hurrison
- **Submissions:** 26
- **Solves:** 8

## Description

A sexy girl is waiting for u ...

A two-container chat challenge (server + bot) with a **zero-click / sandbox**
theme — the per-team flag template is
`trusted_partners_break_hearts_and_sandboxes_without_a_single_click`. The
`server` runs a custom chat server (`chatserver`, mTLS on TCP 8443); the `bot`
is a victim running the Electron-based **R3Chat** desktop client under Xvfb,
logged in and connected to the server. Players interact with the server over
raw TCP; the intended solve delivers a malicious message to the bot (0-click),
gets code execution in the Electron client (`ELECTRON_DISABLE_SANDBOX=1`,
`--no-sandbox`), and reads the flag via the setuid `/readflag` (`/flag` is
root-only `0400`).

Attachment password: `cTl5hwoP67swmMxI` (see `attachment/links.txt`).

## Files

- `src/` — build source for both images:
  - `docker-compose.yml` — builds `server` + `bot`; passes `FLAG`
    (placeholder `r3ctf{replace_me_with_the_real_flag}`).
  - `server/` — `Dockerfile` (debian:bookworm-slim), the
    `chatserver-1.0.0-linux-amd64` binary (12 MB), and `certs/` — the
    **DMChat mTLS material**: Root CA (`ca.crt`/`ca.key`), `dmchat-server`
    and `dmchat-client` keypairs (challenge design material; the server
    image bakes `ca.crt` + `server.crt` + `server.key`).
  - `bot/` — `Dockerfile` (installs the Electron client deb under Xvfb,
    builds the setuid `/readflag` from `readflag.c`, locks `/opt/R3Chat`
    read-only, runs as uid 1001), `entrypoint.sh` (dynamic flag → `/flag`,
    then env scrub), `readflag.c`, `r3chat-client_1.0.0_amd64.deb` (73 MB).
  - The Windows installer `R3Chat-Setup-1.0.0.exe` (79 MB) is **not in git** —
    it is the player handout and is hosted externally (see
    `attachment/links.txt`); no Dockerfile uses it.
- `attachment/links.txt` — download links for the player handout (hosted
  externally; password `cTl5hwoP67swmMxI`).
- `checker.rx` — platform flag checker (dynamic per-team flag:
  `dynamic-leet.rx`, template
  `trusted_partners_break_hearts_and_sandboxes_without_a_single_click`,
  encrypt key `Z79BeyZB3zJLMkvT`), copied from the ret2shell export.

## Deployment

Two images, built from `src/`:

```sh
cd src && FLAG='r3ctf{...}' docker compose up -d --build
```

or build/push individually (contexts: `src/server`, `src/bot`):

| image | tag | CPU | mem | port |
|---|---|---|---|---|
| server | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3chat-server:latest` | 1.0 | 512Mi | 8443/tcp (raw, mTLS) |
| bot | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3chat-bot:latest` | 2.5 | 2048Mi | — |

Platform `env.toml`: `internet = true`, unprivileged. Build/push from the ops
host only (see `DEPLOY.md`).

Dynamic flag: the platform injects `$FLAG` into the **bot** container;
`bot/entrypoint.sh` requires it, writes `/flag` (`0400 root`), then scrubs
the env. The flag is only readable via the setuid `/readflag`. Per-team flags
are derived by `checker.rx` from the team id (template + encrypt key above).
Platform score rule: initial 1000 / minimum 100 / decay 30.
