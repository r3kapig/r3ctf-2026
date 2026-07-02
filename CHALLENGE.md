# R3CTF 2026 Challenges

Registry: `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest`

## 镜像列表（需要 build / push）

| 名字 | 镜像名 | CPU | 内存 | 状态 |
|---|---|---|---|---|
| eazyvpn | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/eazyvpn:latest` | 0.1 | 128m | pushed ✓ |
| HEuristic | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/heuristic:latest` | 0.5 | 256m | pushed ✓ |
| rECp1cG | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/recp1cg:latest` | 0.1 | 128m | pushed ✓ |
| P1gROXY | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/p1groxy:latest` | 0.1 | 128m | pushed ✓ |
| netshare | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest` | 0.5 | 256m | pushed ✓ |
| trustedhash | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/trustedhash:latest` | 1.0 | 2g | pushed ✓ |
| r3map | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3map:latest` | 2.0 | 3g | pushed ✓ |
| TsukisRhythmGame | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/tsukisrhythmgame:latest` | 0.1 | 128m | pushed ✓ |
| definitely-not-a-web-chal | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/definitely-not-a-web-chal:latest` | 0.5 | 256m | pushed ✓ |
| r3ticket | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3ticket:latest` | 1.0 | 512m | pushed ✓ |
| z3kapig | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/z3kapig:latest` | 2.0 | 1g | pushed ✓ |

## 本地运行 / 纯附件（不 push 镜像）

| 名字 | 说明 |
|---|---|
| whisper | 本地跑通即可，不构建/push。部署：`cd deploy && ./run.sh <public-ip> [N]`，`[N]` 为并发设备上限（超过则排队），已实现动态 flag。运行需 KVM + Android AVD，约 2 CPU / 4G。 |
| pewpew | 纯附件：`attachment/{to_player.zip, r3ctf-pewpew.rdp}`（Windows LFH，连外部 Windows Server 2025 主机）。 |
| Time Capsule | 纯附件：`attachment/` 下的取证/隐写链文件。 |
| teRRibleRing | 纯附件：`attachment/{task.sage, samples.txt}`（Ring-LWE，SageMath，离线分析）。 |
| lift | 纯附件：`attachment/chall`（静态 ELF，IR / lambda VM 逆向，离线分析）。 |

## 备注

- **netshare**：push 的是 per-team 的 `netshare-bridge` pod 镜像（Flask，轻量）。控制器侧（`kubernetes-on-demand-main/`）需 `network_mode: host` + 挂载 `/var/run/docker.sock`，每个队伍起一个 kind 集群，控制器主机建议 2–4G 内存。
- **trustedhash**：push 的是 per-team 部署的 `trusted-hash-portal` 镜像（entrypoint `trusted-hash-portal`，约 7.57GB，远端已有故直接 retag，未重新 build）。运行需 `--privileged` + KVM，每队一个实例并通过 `FLAG` 注入动态 flag。选手开发用的 `nix-builder` 镜像是单独的重型 Nix 构建，未推送。
- **whisper**：多服务栈（backend / judge / victim-runner），victim-runner 运行需 `--privileged --device /dev/kvm`。现部署在 `vm.ctf2026.r3kapig.com`（`./run.sh 103.164.32.106 2`）。支持 **Model B**：`auth-pod/` 是 per-team 选手入口（鉴权 + 代理 lease/status/APK + 推 flag），judge 不暴露给选手。
- **r3map**：Linux kernel pwn，每次连接起一个 QEMU/KVM VM（`bzImage` + `initramfs`，`-m 2048 -smp 4`）。运行需 `--device /dev/kvm` + `seccomp=unconfined`，flag 通过 `FLAG` 注入 VM 内只读挂载。
