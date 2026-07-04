# someday 运维指南

- 题目镜像: `/root/someday/ctf.qcow2`
- 实例配置: `/root/someday/wk.json`（8 个实例，端口 28400–28407）
- 玩家账号: `hacker` / `hacker123@`（在 `run.py` 里写死，所有实例共用）
- flag: `r3ctf{pwn2own_for_the_win!!!!!!!}`（全题同一个）
- tmux session: `someday`
- 日志: `/tmp/logs/<port>.log`

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

> 8 台实例是同时启动的，所以 30 分钟到点也几乎同时到，会有一波约 1.5–2 分钟
> 的"全 8 台同时重启"窗口（Windows 开机 + provisioning）。这是正常的；玩家断开
> 重连即可。

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
ss -ltnp | grep -E ':2840[0-7]'                    # 8 个端口应都在 LISTEN
ps -eo args | grep qemu-system-x86_64 | grep -v android   # 应有 8 个 qemu
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
