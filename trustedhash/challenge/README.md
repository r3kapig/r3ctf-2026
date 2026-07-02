# Trusted Hash Challenge Source

This directory is the player-facing source bundle for the Trusted Hash
challenge.

## Challenge Background

The hosted challenge has two roles:

- The **player VM** is the Linux VM you control. You can log in over SSH,
  inspect it through VNC, and do whatever you want.
- The **checker**, also called the **attester**, is the remote service that
  periodically verifies your player VM and sends the current CTF flag through
  the attested flow.

The interesting boundary is not Unix user separation inside the player VM: the
checker relies on a few trusted computing techniques.

During the hosted run, the checker periodically connects to the
`trusted_hash_agent` service inside your player VM. The agent proxies requests
into the `trusted_hash` kernel module, which talks to the TPM. The checker
verifies the player VM's trusted state, sends the current CTF flag through that
attested flow, and expects the player VM to return the correct trusted hash.
The flag plaintext is meant to exist only inside this checker flow, not as a
file on disk.

Before the player VM is exposed to you online, the operator boots it privately
once and captures the initial trusted PCR/module baseline that future checker
runs will accept. Your goal is to understand or subvert this design while the
checker continues to accept your player VM.

## Layout

- `trusted_hash_kmod/`: the Linux kernel module loaded in the player VM.
- `trusted_hash_agent/`: the userspace TCP proxy running in the player VM.
- `trusted_hash_common/`: the length-prefixed JSON/base64 protocol shared by
  the Rust binaries.
- `trusted_hash_attester/`: the checker/attester side implementation.
- `os/`: the NixOS image definition for the player VM.
- `scripts/`: helper scripts to build a reusable release image, create a VM
  directory from it, and start that VM locally.

This directory contains the source and helper scripts needed for local
reproduction of the challenge flow.

## Development Environment

All build and runtime tools needed by players are provided by the Nix dev shell:
Rust, QEMU, swtpm, tpm2-tools, OpenSSL, sbctl, virt-firmware helpers, and the
kernel module build toolchain. You do not need to install Nix yourself if you
use the provided Docker image.

The official Docker image is:

```sh
<image>:<tag>
```

It contains Nix with flakes enabled, the challenge dev shells, pre-generated
local reproduction Secure Boot and module-signing keys, and a warmed Nix store
from a full release build. That cache is included so you do not spend your
first local run recompiling Linux.

From this `challenge` directory:

```sh
docker pull <image>:<tag>

docker run --rm -it --privileged \
  -v "$PWD:/work" \
  -w /work \
  -p 31337:31337 \
  -p 5900:5900 \
  -p 5700:5700 \
  -p 2222:2222 \
  <image>:<tag>
```

The container starts in `nix develop .#default`. `--privileged` is used for the
local VM workflow because QEMU needs KVM access and the helper scripts create
TPM/NVRAM/disk state.

Editors with Dev Containers support can also open this directory in the
container described by `.devcontainer/devcontainer.json`.

## Local Reproduction

Run Rust tests:

```sh
cargo test
```

Build the userspace binaries explicitly, if you want to inspect them outside
the VM image:

```sh
cargo build --release -p trusted_hash_agent -p trusted_hash_attester
```

Build the C kernel module against the challenge kernel:

```sh
nix build .#trusted_hash_kmod
```

Build a reusable VM release artifact. This compiles/packages the agent, builds
the signed kernel module, builds the NixOS VM image, signs the UKI for Secure
Boot, and exports the public Secure Boot material needed by local VMs:

```sh
./scripts/build-release release/current
```

If you do not want to use the prebuilt Docker image, run the same release build
through a temporary privileged Nix container:

```sh
./scripts/build-release-docker release/current
```

The wrapper uses Docker to provide Nix, enters this directory's default dev
shell for Secure Boot and firmware tooling, keeps the Nix store in a named
Docker volume for repeat builds, and writes the release artifact back into this
source tree.

Create a local VM from that release:

```sh
./scripts/create-vm release/current vm/test1
```

Start the VM. This exposes SSH on host port `60001`, the trusted-hash agent on
host port `31337`, and VNC display `:1` with a websocket on `5701`:

```sh
./scripts/start-vm vm/test1
```

In another shell inside the same Docker container, capture the VM's initial
trusted state. This mirrors the private first boot done by the hosted
operator, and writes the PCR digest plus module signer baseline into
`vm/test1/pcr.conf`:

```sh
./run-attester --addr 127.0.0.1:31337 \
  --pcr-profile hard \
  --learn-pcr-digest \
  --write-pcr-config vm/test1/pcr.conf \
  --ek-root-ca vm/test1/ca/swtpm-localca-rootca-cert.pem \
  --ek-issuer vm/test1/ca/issuercert.pem
```

After that baseline is captured, run the normal attester flow against the same
VM:

```sh
./run-attester --addr 127.0.0.1:31337 \
  --config vm/test1/pcr.conf \
  --ek-root-ca vm/test1/ca/swtpm-localca-rootca-cert.pem \
  --ek-issuer vm/test1/ca/issuercert.pem
```

The hosted challenge follows the same shape: private baseline capture first,
then repeated attester runs that send the dynamic flag and expect the trusted
hash result.

## Maintainer Image Build

The player image is built from `docker/nix-builder.Dockerfile`:

```sh
docker buildx create --driver-opt image=moby/buildkit:master  \
                     --use --name insecure-builder \
                     --buildkitd-flags '--allow-insecure-entitlement security.insecure'
docker buildx use insecure-builder
docker buildx build --allow security.insecure -f docker/nix-builder.Dockerfile -t <image>:<tag> .
docker push <image>:<tag>
```

The Dockerfile intentionally performs one `./scripts/build-release` during
image creation. The release output is discarded, but the generated local keys
and expensive Nix store paths remain in the image for players to reuse.
