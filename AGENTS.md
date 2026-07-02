# AGENTS.md — r3ctf-2026 运维指南

本文件面向**完全没接触过本项目**的人，说明这个仓库是什么、目录怎么组织、以及
「整理一道题 → 远端构建 → 推送镜像 → 登记 CHALLENGE.md → 提交 git」这套流程怎么走，
并记录已经踩过的坑，避免重复踩。

---

## 1. 这是什么

`r3kapig/r3ctf-2026` 仓库的 **`infra` 分支**，存放 R3CTF 2026 各题的**构建 / 部署源
码**。镜像统一推到：

```
registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<challenge>:latest
```

平台按 flag 注入方式在选手连接时动态下发 flag，仓库里**只放占位 flag**，真 flag 不进 git。

---

## 2. 目录结构（约定）

每道题按 `<分类>/<题目>/` 组织，遵循 `reference/creating-ctf-docker/SKILL.md`（r3ctf-2025
同款约定）：

```
<Category>/<challenge>/
├── README.md            # CTFd metadata：Category / Author / Difficulty / Description / Files
├── infra.sh             # 构建 + 运行脚本（从 deploy/ 内执行）
├── attachment/          # 给选手的附件（绝不放真 flag）
└── deploy/              # 线上容器 / 基础设施
    ├── Dockerfile
    ├── service/docker-entrypoint.sh   # flag 注入 + 启动服务（如有）
    ├── config/          # xinetd / nginx / apache 配置（如有）
    ├── src/             # 题目源码 / 二进制
    └── docker/docker-compose.yml      # 本地一键测试（build: ../）
```

**flag 注入标准块**（写在 entrypoint 头部，解析后立刻 scrub）：

```sh
if [ -n "$FLAG" ]; then
    INSERT_FLAG="$FLAG"
    export FLAG=no_FLAG
    FLAG=no_FLAG
else
    INSERT_FLAG="flag{TEST_Dynamic_FLAG}"
fi
# 然后把 INSERT_FLAG 写到 /flag 或 DB 或 argv，再启动服务
```

> 复杂多组件题（whisper / netshare / trustedhash / r3map）不强求 `deploy/{src,service}`
> 的细分，只保留顶层 `README.md + infra.sh + attachment/ + deploy/`，内部结构保持原样。

---

## 3. 基础设施

| 项 | 值 |
|---|---|
| 远端构建机 | `r3kapig@ops.ctf2026.r3kapig.com`（hostname `r3ctf-ops`） |
| 架构 | `x86_64`，4 核，15Gi RAM，80G 磁盘，Docker 29.6 + buildx |
| 远端构建目录 | `~/r3ctf-build/<challenge>/` |
| Registry | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<challenge>:latest` |
| Registry push | 从 ops 主机**直接 push 即可，无需 docker login**（IP 白名单） |
| Git 仓库 | `https://github.com/r3kapig/r3ctf-2026.git`，分支 `infra` |
| Git 认证 | `gh auth setup-git`（github.com 走 gh token，非交互） |
| SSH | key-based（`BatchMode=yes` 可直连） |

> 远端**没有 `rsync`**，传文件用 `tar | ssh tar`（见 §5）。

---

## 4. 标准流程：新增 / 整理一道题

1. **摸清题目**：判断分类、flag 注入方式、是否需要 KVM / 特殊权限、端口。
2. **整理目录**：按 §2 约定落到 `<Category>/<challenge>/`，写 `README.md` + `infra.sh`，
   把容器文件归进 `deploy/`，选手附件归进 `attachment/`。
3. **检查 flag**：`grep -rEn 'flag\{|r3ctf\{|R3CTF\{'` 全目录扫一遍，**真 flag 不能进 git**，
   只剩占位 / 题目内 decoy。
4. **远端构建 + 推送**：见 §5。
5. **登记 `CHALLENGE.md`**：类型 / 名字 / 镜像名 / CPU / 内存 / 特殊需求。
6. **提交 git**：见 §7。

---

## 5. 远端构建 playbook

### 5.1 传构建上下文（clean-tar，避 macOS 坑）

macOS 文件的 quarantine xattr 经 `tar` 会变成 `._*` AppleDouble 文件，污染构建（见 §8）。
统一用：

```sh
COPYFILE_DISABLE=1 tar --exclude='._*' --exclude='.DS_Store' --exclude='.git' \
  -czf - -C <本地deploy或题目根> . \
  | ssh -o BatchMode=yes r3kapig@ops.ctf2026.r3kapig.com \
    'rm -rf ~/r3ctf-build/<name> && mkdir -p ~/r3ctf-build/<name> && tar xzf - -C ~/r3ctf-build/<name>'
```

> `tar: Ignoring unknown extended header keyword 'LIBARCHIVE.xattr...'` 这类警告是无害的
> （GNU tar 忽略 macOS xattr）。真正要防的是 `._*` 文件——上面命令已经 exclude，
> 传完后可用 `find ~/r3ctf-build/<name> -name '._*' | wc -l` 确认是 0。

### 5.2 构建 + 推送

```sh
ssh r3kapig@ops.ctf2026.r3kapig.com \
  'cd ~/r3ctf-build/<name> \
   && docker build -t registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest . \
   && docker push registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest'
```

如果 Dockerfile 不在上下文根（如 r3map 在 `deploy/Dockerfile`）：

```sh
docker build -f deploy/Dockerfile -t <reg>/<name>:latest <context>
```

### 5.3 验证

```sh
ssh r3kapig@ops.ctf2026.r3kapig.com \
  'docker buildx imagetools inspect registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest'
```

### 5.4 资源 / 并发

- 构建机 15Gi RAM，**不要并行跑多个重型构建**（曾把机器打到 OOM 重启）。
- 重型构建（SEAL / Nix）单独跑；SEAL 建议把 `cmake --build build -j` 改成 `-j4` 限并行。
- 轻量题（Python / 小 C++）可以并行 2–3 个。

---

## 6. 各题速查

| 类型 | 名字 | 镜像 | CPU | 内存 | 特殊 |
|---|---|---|---|---|---|
| Crypto | HEuristic | `…/heuristic:latest` | 0.5 | 256m | SEAL CKKS，构建较慢 |
| Crypto | rECp1cG | `…/recp1cg:latest` | 0.1 | 128m | Coppersmith，socat TCP 9999 |
| Crypto | teRRibleRing | （纯附件） | — | — | Ring-LWE，SageMath，离线分析 |
| Pwn | P1gROXY | `…/p1groxy:latest` | 0.1 | 128m | C++ 反代 + Flask |
| Pwn | pwn-eazyvpn | `…/pwn-eazyvpn:latest` | 0.1 | 128m | TLS VPN + SOCKS5 pivot |
| Misc | netshare | `…/netshare:latest` | 0.5 | 256m | push 的是 bridge pod；控制器需 `network_mode: host` + `/var/run/docker.sock` |
| Misc | trustedhash | `…/trustedhash:latest` | 1.0 | 2g | portal 镜像（7.57G），运行需 `--privileged` + KVM |
| Pwn | r3map | `…/r3map:latest` | 2.0 | 3g | kernel pwn，QEMU/KVM，运行需 `--device /dev/kvm` + `seccomp=unconfined` |
| Pwn | whisper | （不 push） | — | — | **仅本地运行**：`cd deploy && ./run.sh <public-ip> [N]` |
| Pwn | pewpew | （纯附件） | — | — | Windows LFH，`attachment/r3ctf-pewpew.rdp` |
| Misc | Time Capsule | （纯附件） | — | — | `attachment.7z`（55M） |

`…` = `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700`。完整资源见 `CHALLENGE.md`。

---

## 7. Git 流程

```sh
git add <files>
git commit -m "..."
git push origin infra        # infra 分支已 set-upstream
```

### `.gitignore` 已经处理

- `/reference/`（1.2G 参考资料 / 2025 旧题，不属于本仓库）。
- `.DS_Store` / `**/._*`（macOS 垃圾）。
- 大文件：
  - `Pwn/whisper/attachment/whisper-local-stack.7z`（481M）→ 走网盘，
    占位 `Pwn/whisper/attachment/whisper-local-stack.txt`（**链接待补**）。
  - `Misc/Time Capsule/attachment/`（未压缩目录）→ 仓库里只保留压缩好的
    `attachment.7z`。

### GitHub 文件大小

- **>100MB 硬拒**，>50MB 给 warning（GH001）。
- 大附件优先压缩成 7z（仍 >100MB 就走网盘 + `.txt` 占位，不要强塞）。
- 提交前用 `find . -type f -size +50M` 扫一遍，避免 push 被拒。

---

## 8. 已知坑 & 修复（重点）

### 8.1 macOS `._` AppleDouble 文件破坏 C/C++ 构建

- **现象**：`docker build` 报 `._message.cpp: error: 'Mac' does not name a type` 之类。
- **原因**：macOS 的 quarantine / provenance xattr 经 bsdtar 打包后，在 Linux 端被
  GNU tar 还原成 `._<file>` 实体文件，被 `cmake file(GLOB ...)` 当源码编译。
- **修复（已做）**：
  1. 本地 `xattr -cr <dir>` 清掉 xattr；
  2. 传输用 `COPYFILE_DISABLE=1 tar --exclude='._*' ...`；
  3. 题目加 `.dockerignore`：`**/.git` / `**/.DS_Store` / `**/._*`；
  4. 若远端已有污染：`find <dir> -name '._*' -delete`。

### 8.2 远端构建机 OOM 重启

- **现象**：SSH 突然 `banner exchange timeout`，恢复后 `uptime` 只剩 1 分钟（机器重启了）。
- **原因**：SEAL（`-j` 无限制）+ p1groxy + netshare 三个并发构建把 15Gi 打满。
- **修复**：重型构建串行跑，SEAL 限 `-j4`；机器已升级，但仍别滥用并发。

### 8.3 真 flag 泄漏到 git

- 历史问题：HEuristic 的 `docker-compose.yml` 写死了真 flag；P1gROXY 把真 flag 在
  Dockerfile 里 `printf > /flag.txt` 烘烤进镜像。
- **修复**：全部改成运行时 `$FLAG` 注入（entrypoint 写 `/flag.txt` 后 scrub），
  仓库只留占位。新增题目务必 `grep` 自查。

### 8.4 trustedhash 不要重新 build

- 远端已有构建好的 `trusted-hash-portal:local`（7.57G）。直接
  `docker tag trusted-hash-portal:local <reg>/trustedhash:latest && docker push`，
  不要重新跑 Nix 构建（`buildx --allow security.insecure` + 完整 NixOS，半小时以上且易失败）。

### 8.5 whisper 部署

- whisper 不 push 镜像，只在 KVM 主机上跑：`cd deploy/deploy && ./run.sh <public-ip> [N]`
  （N = 并发设备上限）。现部署在 `vm.ctf2026.r3kapig.com`。
- victim 镜像 build 拉 debian base 时会被 docker.io 的 CloudFront CDN 在境内 reset；
  用 daocloud mirror 拉好 base 镜像并 tag 成官方名：`docker pull
  docker.m.daocloud.io/library/debian:bookworm-slim && docker tag
  docker.m.daocloud.io/library/debian:bookworm-slim debian:bookworm-slim`（nginx 同理）。
- 它的 481M `whisper-local-stack.7z` 走网盘（见 `.gitignore` + 占位 `.txt`）。

### 8.6 `docker compose config` 报 FLAG required

- r3map 的 compose 用 `FLAG: "${FLAG:?FLAG is required}"`，本地裸跑
  `docker compose config` 会失败。**这是预期的**（FLAG 未设），不是配置错误；
  验证用 `FLAG=test docker compose config`。

---

## 9. whisper Model B（per-team auth pod）

把 judge 藏起来、给每队一个 pod 作为唯一入口：

```
player ──X-Pod-Token──► auth pod ──X-Admin-Token + team_id──► judge (internal)
player ──────────────────────────────────────────────────────► backend (public, in APK)
```

- **judge 改动**（已做）：
  - `team_flags.py`：per-team flag **以 `/data/team_flags.json` 文件为准**（每次读写都
    落文件，原子 `os.replace`，没有内存缓存）。
  - `POST /admin/flags`（admin 鉴权）：auth pod 把 flag 推到这里。
  - `/lease` `/release` `/status`：admin 鉴权 + body/query 取 `team_id`（已删 team token +
    `teams.json`，pool 直接按 `team_id` 索引）。
  - `pool._do_assign`：**必须有** pushed flag（`team_flags.get(team_id)`），否则拒绝租约
    （已删除 `flag_stego.make_flag`，judge 不再产 flag）。
  - `worker._flag_accepted`：直接和 pushed flag 比对（flag-sharing / stegano 校验交给平台 checker）。
- **auth pod**（`Pwn/whisper/auth-pod/`）：
  - 环境：`TEAM_ID` / `POD_TOKEN`（随机）/ `WHISPER_JUDGE_URL`（内网）/
    `WHISPER_BACKEND_URL`（公网）/ `WHISPER_ADMIN_TOKEN` / 可选 `FLAG`（不设则用
    `R3CTF{TEST_FLGA}` 占位）。
  - 启动推 flag，运行时代理 `lease / release / status / download/whisper.apk`。
- **部署**：judge + backend + victim pool 用 `deploy/deploy/run.sh` 起（judge 不暴露）；
  平台（ret.sh / k8s-on-demand）每队起一个 auth-pod，给选手 pod URL + `POD_TOKEN`。
- backend 必须公网暴露（APK 直连），judge 必须内网（只让 pod 访问）。

详见 `Pwn/whisper/README.md` 和 `Pwn/whisper/auth-pod/README.md`。

---

## 10. 参考资料

- `reference/creating-ctf-docker/SKILL.md` —— 本题仓库采用的约定来源（flag 注入、
  xinetd/socat/直接监听选型、各分类 skeleton）。
- `reference/r3ctf-2025/` —— 40 道 2025 真题实例（已被 `.gitignore`，本地参考用）。
- `CHALLENGE.md` —— 当前所有镜像 / 资源 / 特殊部署需求的权威清单。
