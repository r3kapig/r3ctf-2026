# ezvpn

- **Category:** Pwn
- **Author:** Squeasp
- **Difficulty:** Easy
- **Wave:** 2
- **Points:** 
- **Solves:** 

## Description

simple sslvpn...but something more

A pwn challenge built around a custom SSL-VPN gateway: a stripped TLS binary
(`fw_ctf_host` on the live instance, `eazyvpn` in the handout) listens on port
4433 with a self-signed certificate (`CN=ezvpn.local`) and its own bundled
`lib/` (custom loader + zlib/zstd). Players connect over TLS, authenticate with
the VPN credentials, and exploit the service to read the flag.

The flag lives at `/flag` (also copied to `/app/flag`, both mode 444) inside the
container. On the live instance the VPN password is random per container start;
the player handout ships a fixed test password so the environment can be
reproduced locally (`SSLVPN_USER=Mr.Slopper`,
`SSLVPN_PASS=QWZ0M3JBVTdoWWU1`).

## Files

- `attachment/` — player handout: full local-repro build context (`Dockerfile`,
  `docker-compose.yml`, `entrypoint.sh`, the `eazyvpn` binary, and its `lib/`).
  Players can `docker compose up` to reproduce the environment locally; the
  attachment entrypoint uses a fixed test password and no dynamic flag.
- `deploy/` — live container build context: `Dockerfile` (ubuntu:26.04, openssl
  + gdb, generates the server cert at build time), `docker-compose.yml`,
  `entrypoint.sh` (flag injection + password generation + restart loop), the
  `fw_ctf_host` TLS gateway binary, and its `lib/`.
- `infra.sh` — build + run script; run from inside `deploy/`
  (`cd deploy && ../infra.sh`).

## Deployment

Docker container. The flag is injected dynamically: `entrypoint.sh` reads
`$FLAG` (also `$GZCTF_FLAG` / `$DASFLAG`) at runtime, writes it to `/flag` and
`/app/flag`, then scrubs the env (`FLAG=no_FLAG`). If no flag env is set it
falls back to `flag{TEST_Dynamic_FLAG}`; only a placeholder is baked into the
image. The container also generates a random 16-char `SSLVPN_PASS` per start
(user `Mr.Slopper`) and runs `fw_ctf_host` in a restart loop on :4433.

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/ezvpn:latest`
- **Ports:** container `4433` (TLS); `infra.sh` maps host `30004:4433`, the
  compose files map `9000:4433`
- **Resources:** `--cpus 0.1 --memory 128m`
