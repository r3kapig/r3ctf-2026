# someday 运维指南

- 题目镜像: `/root/someday/ctf.qcow2`
- 实例配置: `/root/someday/wk.json`（8 个实例，端口 28400–28407）
- 玩家账号: `hacker` / `hacker123@`（在 `run.py` 里写死，所有实例共用）
- flag: `r3ctf{pwn2own_for_the_win!!!!!!!}`（全题同一个）
- tmux session: `someday`
- 日志: `/tmp/logs/<port>.log`

---

## 0. 关于 lifetime（`--timeout`）

每个 `run.py` 启动时带一个 `--timeout <秒>`。它会 `sleep` 这么久，然后
**自动关停 qemu + 代理并清理临时目录**。`wk.json` 里 `timeout=86400` 即
**启动 24h 后该实例自动退出**。

要改时长：编辑 `wk.json` 里每个条目的 `"timeout"` 字段（单位秒），然后重启。
常用值：3 天 `259200`，7 天 `604800`，30 天 `2592000`。

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
