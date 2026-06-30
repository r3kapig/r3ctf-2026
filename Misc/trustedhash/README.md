# trustedhash

- **Category:** Misc
- **Author:** 
- **Points:** 
- **Solves:** 

## Description

TPM / secure-boot 证明题。每支队伍获得一个独立的 NixOS 玩家 VM（SSH/VNC 可登录），
远端 attester 周期性校验 VM 并通过 TPM-attested 通道下发当前 flag。

## Architecture

- `challenge/` — 玩家侧源码：NixOS 玩家 VM（`os/`）、Rust workspace
  （`trusted_hash_agent` / `trusted_hash_attester` / `trusted_hash_common`）、内核模块
  （`trusted_hash_kmod`）、以及 `docker/nix-builder.Dockerfile`（玩家开发镜像）。
- `operator/` — 运营侧 portal：Rust workspace（`trusted_hash_portal`）+
  `docker/player-portal.Dockerfile`，负责为每队 provision 一个 VM 并注入动态 flag。

## Deployment

per-team portal 镜像已 build/push：
`registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/trustedhash:latest`

每队运行一个 portal 实例（需 `--privileged` + KVM，并注入动态 flag）：

```sh
docker run --rm -d --privileged --device /dev/kvm \
  -e FLAG=<per-team-flag> \
  -p <host-ssh>:2222 -p <host-agent>:31337 \
  registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/trustedhash:latest
```

完整参数见 `operator/README.md`。

玩家开发镜像（`challenge/docker/nix-builder.Dockerfile`，基于 `nixos/nix`，需
`buildx --allow security.insecure` 构建）是单独的重型 Nix 构建，未推送。

## Files

- `challenge/` — 玩家 VM + agent/attester/kmod 源码。
- `operator/` — per-team portal（已 push 为 `…/trustedhash:latest`）。
