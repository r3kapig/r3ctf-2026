# ploys

- **Category:** Pwn
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

Perhaps this is already technology from a bygone era...

A small C binary (kept function symbols; some layout globals stripped) behind a
`seccomp` sandbox, served over raw TCP via `socat`. Pwn it to read `/flag`.

## Files

- `attachment/` — player handout: the `ploys` binary, matching Ubuntu 24.04
  amd64 `libc.so.6` + `ld-linux-x86-64.so.2`, and a local Docker runner
  (`Dockerfile`, `docker-compose.yml`, `start.sh`).
- `deploy/` — the live container (builds from `attachment/ploys` + `deploy/start.sh`).
- `source/` — the C source (`ploys.c`, `seccomp.c`, `Makefile`).
- `solve.py` — reference exploit.

## Deployment

The flag is injected at runtime via `$FLAG` (`start.sh` writes it to `/flag`,
`0440 root:nogroup`, then drops to the `ctf` user). Only a placeholder is needed.

The deploy image copies `attachment/ploys` directly so the public attachment and
the remote binary stay byte-for-byte identical. Build context is the `ploys/`
root (the Dockerfile references both `attachment/ploys` and `deploy/start.sh`).

```sh
cd ploys && ./infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/ploys:latest`
- **Port:** container `1337` (socat), host `1337`
- **Flag env:** `FLAG`
