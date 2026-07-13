# trustedhash

- **Category:** Misc
- **Author:** starcatmeow
- **Difficulty:** Hard
- **Wave:** 3
- **Points:** 
- **Solves:** 

## Description

The machine is yours, but the trust is not.

Players get full control of a Linux VM (root SSH, VNC console) running inside a
per-team portal. A remote checker — the **attester** — periodically verifies the
VM through a TPM-attested flow (Secure Boot, measured kernel module) and sends
the current per-team flag into the VM, expecting the correct SHA-256 hash back
through the trusted path. The goal is to recover the flag — e.g. by forging the
hash response or extracting the flag from the attested flow — without breaking
the checker's trust.

The hosted challenge has two roles:

- The **player VM** is the Linux VM you control: log in over SSH, inspect it
  through VNC, do whatever you want.
- The **checker/attester** is the remote service that periodically verifies the
  VM and feeds the current CTF flag through the attested flow.

At VM creation the portal provisions a one-time root password and a VNC
password, returned only in the create response; the CTF platform exposes the
SSH/VNC/agent addresses to the player.

## Files

- `challenge/` — player-facing source bundle: NixOS player VM config (`os/`),
  Rust workspace (`trusted_hash_agent` / `trusted_hash_attester` /
  `trusted_hash_common`), the trusted kernel module (`trusted_hash_kmod`),
  build/run scripts (`scripts/`, `run-agent`, `run-attester`), and
  `docker/nix-builder.Dockerfile` (player dev image). See `challenge/README.md`.
- `operator/` — operator-side per-team portal: Rust workspace
  (`trusted_hash_portal`, owns the web UI, QEMU lifecycle, noVNC proxy, and
  attester loop), `docker/player-portal.Dockerfile` + compose example, and
  `docs/deployment-services.md`. See `operator/README.md`.
- `flake.nix`, `flake.lock` — top-level Nix operator workspace: builds
  `trusted_hash_portal` and its runtime env (QEMU, swtpm, tpm2-tools, noVNC,
  …) plus operator dev shells.
- `infra.sh` — deploy note: run one portal per team from the portal image.
- `.gitignore` — excludes `challenge/.secrets/` (Secure Boot / module-signing
  private keys, operator-only) and release/build outputs.

## Deployment

One `trusted_hash_portal` instance runs per team (per-team pod, owns exactly
one VM). The portal image is
`registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/trustedhash:latest`.

Run one portal per team — needs `--privileged` + KVM, with the dynamic
per-team flag injected via `FLAG` (the portal passes it to the internal
attester as `CTF_FLAG`):

```sh
docker run --rm -d --privileged --device /dev/kvm \
  -e FLAG=<per-team-flag> \
  -p <host-ssh>:2222 -p <host-agent>:31337 \
  registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/trustedhash:latest
```

VM exposure is fixed: SSH `2222`, trusted-hash agent `31337`, raw VNC `5900`;
the QEMU VNC websocket (`5700`) stays loopback-only behind the portal's noVNC
proxy. Portal HTTP listens on `TH_PORTAL_ADDR` (default `0.0.0.0:8080`);
attester interval `TH_TEST_INTERVAL_SECONDS` (default `30`). Persistent state
lives under `/var/lib/trusted-hash`.

Rebuilding from scratch (operator side only) is a heavy Nix build:

```sh
# no-secret release artifact (player disk image + public Secure Boot material)
./challenge/scripts/build-release-docker challenge/release/current
# then build the portal image from the repo root
docker build -f operator/docker/player-portal.Dockerfile \
  --build-arg RELEASE_DIR=challenge/release/current \
  -t trusted-hash-portal:local .
```

The player dev image (`challenge/docker/nix-builder.Dockerfile`, based on
`nixos/nix`, built with `buildx --allow security.insecure`, published as
`dongruixuan/trustedhash-devenv:latest`) is a separate heavy Nix build and
lives outside the CTF registry. Full runtime flags and the VM provisioning
flow: `operator/docs/deployment-services.md` and `operator/README.md`.
