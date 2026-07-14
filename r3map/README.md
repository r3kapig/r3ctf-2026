# r3map

- **Author:** Niebelungen
- **Submissions:** 15
- **Solves:** 15

## Description

An East Kernel Challenge in the Age of AI.

A Linux kernel exploitation challenge. Each TCP connection first passes a
sha256 proof-of-work, then gets its own QEMU/KVM virtual machine booting the
provided `bzImage` + `initramfs.cpio.gz` (KASLR, PTI, SMEP, SMAP enabled;
`-m 2048 -smp 4`). The flag is exposed to the guest through a read-only 9p
virtfs share (`mount_tag=r3flag`) that the player must reach from inside the
compromised kernel. Each VM is killed after a 420 s timeout.

## Files

- `attachment/` — player handout: `bzImage`, `initramfs.cpio.gz`, `run.sh`
  (QEMU launcher), `server.py` (PoW + per-connection VM relay), `flag.txt`
  (local placeholder `flag{LOCAL_DEBUG_PLACEHOLDER}`), and a local-repro
  `Dockerfile`.
- `deploy/` — live container: `Dockerfile` (ubuntu:24.04 + qemu-system-x86,
  exposes 1337) and `docker-compose.yml` (`/dev/kvm`, `seccomp=unconfined`).
- `infra.sh` — build + run script (build context is the challenge root).

## Deployment

Dynamic flag: the `FLAG` environment variable is injected at runtime;
`server.py` writes it into `runtime/flagfs/flag` (mode 0400), which `run.sh`
mounts into each guest as the read-only `r3flag` share. The baked-in
`attachment/flag.txt` is only a placeholder. Image:
`registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3map:latest`, port `1337`.

The build context is the challenge root (`deploy/Dockerfile` COPYs
`attachment/...`):

```sh
./infra.sh
# or manually:
docker build -f deploy/Dockerfile -t registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3map:latest .
docker run --rm -d --device /dev/kvm --security-opt seccomp=unconfined \
  -e FLAG='flag{infra_test_flag}' --cpus 2 --memory 3g -p 1337:1337 \
  registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3map:latest
# or, to run locally (needs KVM):
cd deploy && FLAG='flag{test}' docker compose up -d
```

Runtime requires `/dev/kvm` and `seccomp=unconfined`; `infra.sh` limits the
container to 2 CPUs / 3 GB RAM.
