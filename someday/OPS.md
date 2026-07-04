# someday 运维指南

- 题目镜像: `/root/someday/ctf.qcow2`
- 实例配置: `/root/someday/wk.json`（16 个实例，端口 28400–28415）
- 玩家账号: `hacker` / `hacker123@`（在 `run.py` 里写死，所有实例共用）
- flag: `r3ctf{pwn2own_for_the_win!!!!!!!}`（全题同一个）
- tmux session: `someday`
- 日志: `/tmp/logs/<port>.log`

---

## 当前部署实例清单（端口 / 账号 / admin 密码）

玩家密码统一是 `hacker123@`。admin 密码来自 `/root/someday/wk.json`，每台独立：

| 端口 | 账号 | 玩家密码 | admin 密码 | 连接命令 |
|---|---|---|---|---|
| 28400 | `hacker` | `hacker123@` | `WK0!bfb35f84f395993c9` | `ssh -p 28400 hacker@vm.ctf2026.r3kapig.com` |
| 28401 | `hacker` | `hacker123@` | `WK1!58d3344bef41f62f9` | `ssh -p 28401 hacker@vm.ctf2026.r3kapig.com` |
| 28402 | `hacker` | `hacker123@` | `WK2!1e26b308644e12959` | `ssh -p 28402 hacker@vm.ctf2026.r3kapig.com` |
| 28403 | `hacker` | `hacker123@` | `WK3!81549994228439d59` | `ssh -p 28403 hacker@vm.ctf2026.r3kapig.com` |
| 28404 | `hacker` | `hacker123@` | `WK4!bcd7a950898e3a119` | `ssh -p 28404 hacker@vm.ctf2026.r3kapig.com` |
| 28405 | `hacker` | `hacker123@` | `WK5!806aac259532ab519` | `ssh -p 28405 hacker@vm.ctf2026.r3kapig.com` |
| 28406 | `hacker` | `hacker123@` | `WK6!895c5cda65b0bcda9` | `ssh -p 28406 hacker@vm.ctf2026.r3kapig.com` |
| 28407 | `hacker` | `hacker123@` | `WK7!d3d322ced92d3e8c9` | `ssh -p 28407 hacker@vm.ctf2026.r3kapig.com` |
| 28408 | `hacker` | `hacker123@` | `WK8!ee4238ebb5153eabf` | `ssh -p 28408 hacker@vm.ctf2026.r3kapig.com` |
| 28409 | `hacker` | `hacker123@` | `WK9!6512ec3723526973f` | `ssh -p 28409 hacker@vm.ctf2026.r3kapig.com` |
| 28410 | `hacker` | `hacker123@` | `WK10!1b37d39c791b78897` | `ssh -p 28410 hacker@vm.ctf2026.r3kapig.com` |
| 28411 | `hacker` | `hacker123@` | `WK11!2ea1c62da0d1a7b23` | `ssh -p 28411 hacker@vm.ctf2026.r3kapig.com` |
| 28412 | `hacker` | `hacker123@` | `WK12!440e0981c25d65298` | `ssh -p 28412 hacker@vm.ctf2026.r3kapig.com` |
| 28413 | `hacker` | `hacker123@` | `WK13!9a631beddd228c9ea` | `ssh -p 28413 hacker@vm.ctf2026.r3kapig.com` |
| 28414 | `hacker` | `hacker123@` | `WK14!c5ab4d09f705c7221` | `ssh -p 28414 hacker@vm.ctf2026.r3kapig.com` |
| 28415 | `hacker` | `hacker123@` | `WK15!3545e15e6d4ba6044` | `ssh -p 28415 hacker@vm.ctf2026.r3kapig.com` |

flag（全题同一个）: `r3ctf{pwn2own_for_the_win!!!!!!!}`

> 玩家要能从公网连进来，前提是 `vm.ctf2026.r3kapig.com` DNS 指向这台 VM 宿主机、
> 且防火墙/安全组放行 28400–28415。

---

## 0. 关于 30 分钟自动重启（`--timeout`）

`run.py` 现在是一个**死循环**：每轮启动一台全新 qemu（`snapshot=on`，客户机
磁盘改动全部丢弃），用同一套账号/flag 重新 provisioning，跑 `--timeout` 秒，
到点后关掉这一轮 qemu、立刻开始下一轮——如此往复，**进程不会自己退出**。

所以 `--timeout` 的含义 = **每轮运行多久后自动重启一次**。`wk.json` 里
`timeout=1800` 即 **每 30 分钟重启一次**，每次都是干净客户机，账号 / 密码 /
flag 保持不变（都从 `wk.json` 读，跨轮不变）。

要改间隔：编辑 `wk.json` 里每个条目的 `"timeout"` 字段（单位秒），然后重启该
实例。常用值：30 分钟 `1800`，1 小时 `3600`，2 小时 `7200`。

> **错峰重启**：`run.py` 的**第一轮**运行时长是 `random(0, timeout)` 均匀随机的，
> 所以"第一次重启"（以及之后每隔 30 分钟的重启）就在 30 分钟窗口内均匀散开，
> **不会 16 台同时重启**。稳态下大约每 ~2 分钟有一台实例重启一次（每次约 1.5–2
> 分钟停机，玩家断开重连即可）。`multirun.py` 启动时还会在每台之间加 6 秒间隔，
> 避免 16 台 Windows 同时上电造成的 I/O / CPU 尖峰。
>
> 注意：因为第一轮是 `random(0, timeout)`，个别实例的第一轮可能很短（几十秒），
> 启动后不久就会先重启一次，这是预期行为，重启完就进入稳定的 30 分钟周期。

---

## 1. 启动（全部 8 台）

```bash
tmux new-session -d -s someday \
  'cd /root/someday && python3 -u multirun.py /root/someday/wk.json'
```

## 2. 查看状态

```bash
tmux ls                                            # session 是否存在
tmux capture-pane -t someday -p | tail -40       # 启动日志（含每台密码/flag）
ss -ltnp | grep -E ':284(0[0-9]|1[0-5])'       # 16 个端口应都在 LISTEN
ps -eo args | grep qemu-system-x86_64 | grep -v android   # 应有 16 个 qemu
tail -f /tmp/logs/28400.log                        # 单台 qemu 日志
```

从外网验证某台能通：

```bash
ssh -p 28403 hacker@vm.ctf2026.r3kapig.com      # 密码 hacker123@
```

## 3. 关闭

全部 8 台：

```bash
tmux kill-session -t someday
pkill -f '[f]ile=/root/someday/ctf.qcow2' 2>/dev/null || true   # 清残留 qemu
```

单台（例 28403）：

```bash
tmux kill-session -t sd-28403 2>/dev/null || true
pkill -f '[r]un.py --ssh-port 28403' 2>/dev/null || true
```

## 4. 重启

> 平时**不需要手动重启**——`run.py` 每 30 分钟（`timeout`）自动重启每台实例。
> 只有改了 `wk.json`（flag / 密码 / 端口 / 间隔）或某台卡住时才需要手动重启。

全部 8 台 = 先关后开：

```bash
tmux kill-session -t someday 2>/dev/null
pkill -f '[f]ile=/root/someday/ctf.qcow2' 2>/dev/null || true
sleep 3
tmux new-session -d -s someday \
  'cd /root/someday && python3 -u multirun.py /root/someday/wk.json'
```

单台（用 `run_one.sh` 从 `wk.json` 读该端口参数，例 28403）：

```bash
tmux kill-session -t sd-28403 2>/dev/null
pkill -f '[r]un.py --ssh-port 28403' 2>/dev/null || true
sleep 2
tmux new-session -d -s sd-28403 '/root/someday/run_one.sh 28403'
```

## 5. 改 flag / 密码 / 端口

- flag / 端口 / admin 密码：改 `wk.json` 对应字段，然后「重启全部」。
- 玩家密码：不在 `wk.json` 里，是 `run.py` 顶部的 `HACKER_PASSWORD = "hacker123@"`，
  要改需改 `run.py` 后重启全部。
