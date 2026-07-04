# R3CTF 2026 Challenges

Registry: `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest`

## 镜像列表（需要 build / push）

| 名字 | 镜像名 | CPU | 内存 | 状态 |
|---|---|---|---|---|
| ezvpn | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/ezvpn:latest` | 0.1 | 128m | pushed ✓ |
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
| polys | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/polys:latest` | 0.5 | 128m | pushed ✓ |
| encrypted-activation | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/encrypted-activation:latest` | 1.0 | 512m | pushed ✓ |
| Mafuyuuuuu | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/mafuyuuuuu-{nginx,frontend,backend}:latest`（3 镜像，单 pod） | ~1.7 | ~1.6g | pushed ✓ |
| escape-cet | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/escape-cet:latest` | 1.0 | 1g | pushed ✓ |
| inside | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/inside:latest` | 1.0 | 1g | pushed ✓ |
| r3reach | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3reach:latest` | 2.0 | 3g | pushed ✓ |

## 本地运行 / 纯附件（不 push 镜像）

| 名字 | 说明 |
|---|---|
| whisper | 本地跑通即可，不构建/push。部署：`cd deploy && ./run.sh <public-ip> [N]`，`[N]` 为并发设备上限（超过则排队），已实现动态 flag。运行需 KVM + Android AVD，约 2 CPU / 4G。 |
| pewpew | 纯附件：`attachment/{to_player.zip, r3ctf-pewpew.rdp}`（Windows LFH，连外部 Windows Server 2025 主机）。 |
| Time Capsule | 纯附件：`attachment/` 下的取证/隐写链文件。 |
| teRRibleRing | 纯附件：`attachment/{task.sage, samples.txt}`（Ring-LWE，SageMath，离线分析）。 |
| lift | 纯附件：`attachment/chall`（静态 ELF，IR / lambda VM 逆向，离线分析）。 |
| funnygame | 纯附件：`attachment/FunnyGame.7z`（Unity IL2CPP 游戏逆向，离线分析）。静态 flag。 |
| babycom | VM 主机部署（`vm.ctf2026.r3kapig.com`），不构建/push。8 个 QEMU/KVM Windows 实例，端口 28300–28307，SSH 登录。静态 flag `r3ctf{intended-flag-extraction-without-code-exec}`。运维见 `babycom/OPS.md`。 |
| someday | VM 主机部署（`vm.ctf2026.r3kapig.com`），不构建/push。8 个 QEMU/KVM Windows 实例，端口 28400–28407，SSH 登录。静态 flag `r3ctf{pwn2own_for_the_win!!!!!!!}`。运维见 `someday/OPS.md`。 |

## 备注

- **netshare**：push 的是 per-team 的 `netshare-bridge` pod 镜像（Flask，轻量）。控制器侧（`kubernetes-on-demand-main/`）需 `network_mode: host` + 挂载 `/var/run/docker.sock`，每个队伍起一个 kind 集群，控制器主机建议 2–4G 内存。
- **trustedhash**：push 的是 per-team 部署的 `trusted-hash-portal` 镜像（entrypoint `trusted-hash-portal`，约 7.57GB，远端已有故直接 retag，未重新 build）。运行需 `--privileged` + KVM，每队一个实例并通过 `FLAG` 注入动态 flag。选手开发用的 `nix-builder` 镜像是单独的重型 Nix 构建，未推送。
- **whisper**：多服务栈（backend / judge / victim-runner），victim-runner 运行需 `--privileged --device /dev/kvm`。现部署在 `vm.ctf2026.r3kapig.com`（`./run.sh vm.ctf2026.r3kapig.com 8`，8 台 victim 设备）。`auth-pod/` 是 per-team 选手入口（鉴权 + 代理 lease/status/APK + 推 flag），judge 不暴露给选手。
- **r3map**：Linux kernel pwn，每次连接起一个 QEMU/KVM VM（`bzImage` + `initramfs`，`-m 2048 -smp 4`）。运行需 `--device /dev/kvm` + `seccomp=unconfined`，flag 通过 `FLAG` 注入 VM 内只读挂载。
- **encrypted-activation**：FHE crypto，`task.py` 是 stdin/stdout 服务，`deploy/wrap.py` 绑 TCP **1336** 并把每连接桥接到一个 `task.py` 子进程（纯 CPU Python，无需特殊设备/特权）。flag 通过 `FLAG` 环境变量注入（`deploy/secret.py` 读取）。选手附件含 `task.py / fhe_core.py / lut / setup/client.bin` + 占位 `secret.py`。
- **ezvpn**：SSL-VPN pwn，`fw_ctf_host` 是自监听 TLS 网关，容器内监听 **4433**（`infra.sh` 本地映 `30004:4433`，compose 映 `9000:4433`）。flag 由 `FLAG`/`GZCTF_FLAG`/`DASFLAG` 注入，`entrypoint.sh` 写入 `/flag` 与 `/app/flag`。单容器部署（已移除早期版本的内部 `172.20.0.0/24` decoy 网络）；entrypoint 直接 exec 二进制（不用 ld-linux 当加载器）以保留 ASLR 熵。
- **Mafuyuuuuu**：.NET web（Project SEKAI 主题），**三容器单 pod** 部署（见 `Mafuyuuuuu/deploy/k8s.yaml`）：`backend`（ASP.NET Core 8，`PaperTrailDesk.dll`，8080）/ `frontend`（Vite，4173）/ `nginx`（8089，对外）。三个容器共享 pod 网络命名空间，nginx 反代到 `127.0.0.1:4173`（frontend）和 `127.0.0.1:8080`（backend）——这份 pod 配置（`nginx/nginx.pod.conf`）已 **bake 进 nginx 镜像**，所以 pod 无需 ConfigMap 即可正常启动（`k8s.yaml` 里仍保留 ConfigMap 挂载作为覆盖入口）；本地 compose 则通过 volume 挂载 `nginx/nginx.conf`（service-name 版）。push 的是 3 个镜像 `mafuyuuuuu-{backend,frontend,nginx}:latest`。`k8s.yaml` 里 Service 用 NodePort **30089**（可按平台改）。**动态 flag**：平台通过 `FLAG`/`GZCTF_FLAG`/`DASFLAG` 环境变量注入，backend 的 entrypoint（`deploy/entrypoint.sh`）在启动时把它写入 `/flag`（root 0400，setuid `/readflag` 读取）并 scrub 环境变量；`k8s.yaml` 里 backend 容器用一个 `FLAG` env（占位，平台覆盖）。本地 dev 仍可用 `infra.sh`（docker compose，用 `nginx/nginx.conf` 的 service-name 反代）。
- **escape-cet**：CET（Control-flow Enforcement Technology）pwn，单容器（`ubuntu:24.04`）。`tdocker-server` 监听 TCP **9999**，每连接把 `tcet` 二进制放到 Intel SDE（`environment/sde-external-…`）下以 `-cet 1 -cet-endbr-exe 1` 跑起来（`run_challenge.sh`），选手攻破 CET 读 `/root/flag`。`bin/` 里还有 `drop-exec`（降权）和 `encryptor`（把 flag 加密成 decoy `/flag`，`start.sh` 生成，真正的 flag 在 `/root/flag`）。**动态 flag**：`FLAG` 环境变量（entrypoint 强制要求），写入 `/root/flag` 后 scrub。无需特殊设备/特权（纯 CPU 的 SDE 动态插桩，每连接 CPU 开销中等）。本地 `infra.sh` 映 `30005:9999`。
- **inside**：RLWE + sigma 协议 proof-of-knowledge crypto，单容器（`sagemath/sagemath:9.6`）。`socat` 监听 TCP **9999**，每连接 fork 一个 `sage -python task.py` 会话；选手生成 CRS + RLWE statement，再提交合法 proof 后由 `task.py` 打印 flag。**动态 flag**：`task.py` 从 `$FLAG` 环境变量读取，平台注入即可（`docker-compose.yml` 里仅占位）。无需特殊设备/特权。本地 `infra.sh` 映 `9999:9999`。
- **r3reach**：Minecraft（Paper 26.2 / Java 25）misc，单容器（`eclipse-temurin:25-jre`），监听 TCP **25565**。`R3Reach` 插件把 flag 锁在一个 reach check 后面（"Capture the flag without getting close"），选手需要从比正常更远的距离触发 flag villager；插件命令 `/magic`、`/reset`。**动态 flag**：平台注入 `$FLAG`，`start.sh` 在启动时把它写入 `plugins/R3Reach/config.yml`（`flag:`）后 scrub 环境变量。JVM `-Xms1G -Xmx2G`，容器给 ~3 GB 内存。**vanilla 服务端 jar + 世界已在 build 时 bake 进镜像**（Dockerfile 启动一次 server 等到 `Done` 再关），所以运行期 ~15s 启动、**无需出网**（`--network none` 下也能到 `Done`）；启动时 Paper 会有两个非阻塞的后台调用（`fill.papermc.io` 更新检查 + 一个 metrics/session 调用），有网则静默成功、无网则 harmless 失败，不影响启动。`max-players=1`、adventure、peaceful、void 世界。本地 `infra.sh` 映 `25565:25565`。选手附件是插件 jar（`attachment/R3Reach-1.0.jar`）。
