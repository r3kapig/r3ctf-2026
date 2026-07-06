# r3map

- **Category:** Pwn
- **Author:** Niebelungen
- **Difficulty:** Easy
- **Wave:** 1
- **Points:**
- **Solves:**

## Description

An East Kernel Challenge in the Age of AI.

## Files

- `attachment/` — player handout (`bzImage`, `initramfs.cpio.gz`, `run.sh`,
  `server.py`, and a local-repro `Dockerfile`).
- `deploy/` — live container (`Dockerfile` + `docker-compose.yml`).

## Deployment

The flag is injected via the `FLAG` environment variable at runtime; `server.py`
writes it into the VM's readonly flag mount. Only a placeholder lives in
`attachment/flag.txt`.

The build context is the challenge root (`deploy/Dockerfile` COPYs `attachment/...`):

```sh
docker build -f deploy/Dockerfile -t registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3map:latest .
# or, to run locally (needs KVM):
cd deploy && FLAG='flag{test}' docker compose up -d
```

Runtime requires `/dev/kvm` and `seccomp=unconfined`. The VM is `-m 2048 -smp 4`.
