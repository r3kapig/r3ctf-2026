# polys

- **Category:** Pwn
- **Author:**
- **Difficulty:**
- **Wave:**
- **Points:**
- **Solves:**

## Description

Perhaps this is already technology from a bygone era...

A small C binary (kept function symbols; some layout globals like `polys` /
`poly_degrees` stripped) behind a `seccomp` sandbox, served over raw TCP via
`socat`. Pwn it to read `/flag`.

## Files

- `attachment/` — player handout: the `polys` binary, matching Ubuntu 24.04
  amd64 `libc.so.6` + `ld-linux-x86-64.so.2`, and a local Docker runner
  (`Dockerfile`, `docker-compose.yml`, `start.sh`).
- `deploy/` — the live container (builds from `attachment/polys` + `deploy/start.sh`).
- `source/` — the C source (`polys.c`, `seccomp.c`, `Makefile`).
- `solve.py` — reference exploit.

## Deployment

The flag is injected at runtime via `$FLAG` (`start.sh` writes it to `/flag`,
`0440 root:nogroup`, then drops to the `ctf` user). Only a placeholder is needed.

The deploy image copies `attachment/polys` directly so the public attachment and
the remote binary stay byte-for-byte identical. Build context is the `polys/`
root (the Dockerfile references both `attachment/polys` and `deploy/start.sh`).

```sh
cd polys && ./infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/polys:latest`
- **Port:** container `1337` (socat), host `1337`
- **Flag env:** `FLAG`
