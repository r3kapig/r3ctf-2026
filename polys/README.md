# polys

- **Author:** Csome
- **Submissions:** 65
- **Solves:** 30

## Description

Perhaps this is already technology from a bygone era...

A small C binary behind a `seccomp` sandbox, served over raw TCP via `socat`.
Pwn it to read `/flag`. The binary keeps function symbols for easier reversing,
but debug/type metadata and some layout globals (`polys`, `poly_degrees`) are
stripped. The player handout ships the exact binary plus matching Ubuntu 24.04
amd64 `libc.so.6` / `ld-linux-x86-64.so.2` and a local Docker runner; the
service listens on TCP port `1337`.

## Files

- `attachment/` — player handout: the `polys` binary, matching Ubuntu 24.04
  amd64 `libc.so.6` + `ld-linux-x86-64.so.2`, and a local Docker runner
  (`Dockerfile`, `docker-compose.yml`, `start.sh`, `README.md`).
- `deploy/` — the live container: `Dockerfile` (Ubuntu 24.04 + socat, copies
  `attachment/polys` and `deploy/start.sh`), `start.sh` entrypoint,
  `docker-compose.yml`.
- `source/` — the C source (`polys.c`, `seccomp.c`, `Makefile`).
- `solve.py` — reference exploit.
- `infra.sh` — build + run script (run from the `polys/` root).

## Deployment

The flag is injected at runtime via `$FLAG`: `start.sh` writes it to `/flag`
(`0440 root:nogroup`), unsets `FLAG`, then drops to the `ctf` user and execs
`socat` (60s per-connection timeout) on port 1337. Only a placeholder is baked
into the image.

The deploy image copies `attachment/polys` directly so the public attachment and
the remote binary stay byte-for-byte identical. Build context is the `polys/`
root (the Dockerfile references both `attachment/polys` and `deploy/start.sh`):

```sh
cd polys && ./infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/polys:latest`
- **Port:** container `1337` (socat), host `1337`
- **Flag env:** `FLAG` (dynamic, written to `/flag` then scrubbed)
- **Resources:** `--cpus 0.5 --memory 128m`
