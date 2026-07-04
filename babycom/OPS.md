# babycom 运维指南

- 题目镜像: `/root/babycom/babycom.qcow2`
- 实例配置: `/root/babycom/vs.json`（8 个实例，端口 28300–28307）
- 玩家账号: `hacker` / `<每台随机密码>`（密码见 `vs.json` 的 `user_password` 字段）
- flag: `r3ctf{intended-flag-extraction-without-code-exec}`（全题同一个）
- tmux session: `babycom`
- 日志: `/tmp/logs/<port>.log`

---

## 当前部署实例清单（端口 / 账号 / 密码）

下面这些来自 `/root/babycom/vs.json`，是**当前这一轮**部署的玩家凭据。每次重新
生成 `vs.json` 密码都会变；变了之后用第 3 节的命令重新读取，并更新这里。

| 端口 | 账号 | 密码 | 连接命令 |
|---|---|---|---|
| 28300 | `hacker` | `VU0!28287750d2360b4d9` | `ssh -p 28300 hacker@vm.ctf2026.r3kapig.com` |
| 28301 | `hacker` | `VU1!5726795ad027e0639` | `ssh -p 28301 hacker@vm.ctf2026.r3kapig.com` |
| 28302 | `hacker` | `VU2!9503ae2718e421e49` | `ssh -p 28302 hacker@vm.ctf2026.r3kapig.com` |
| 28303 | `hacker` | `VU3!1c673e17326cb3b09` | `ssh -p 28303 hacker@vm.ctf2026.r3kapig.com` |
| 28304 | `hacker` | `VU4!80fa052d4106f1ad9` | `ssh -p 28304 hacker@vm.ctf2026.r3kapig.com` |
| 28305 | `hacker` | `VU5!a19e1ecca68658779` | `ssh -p 28305 hacker@vm.ctf2026.r3kapig.com` |
| 28306 | `hacker` | `VU6!82cb72596348d0b69` | `ssh -p 28306 hacker@vm.ctf2026.r3kapig.com` |
| 28307 | `hacker` | `VU7!0c6032e7f599c11b9` | `ssh -p 28307 hacker@vm.ctf2026.r3kapig.com` |

flag（全题同一个，在客户机里通过 COM 服务漏洞读取）:
`r3ctf{intended-flag-extraction-without-code-exec}`

> 玩家要能从公网连进来，前提是 `vm.ctf2026.r3kapig.com` DNS 指向这台 VM 宿主机、
> 且防火墙/安全组放行 28300–28307。

---

## 0. 前置依赖（必须先放好，否则启动直接报错）

`run.py` 启动前会从宿主机 `/root/archive/bin/` 把 3 个 COM 服务文件复制进客户机：

```
/root/archive/bin/vaultsvc.exe
/root/archive/bin/vaultsvc_ps.dll
/root/archive/bin/vaultsvc.tlb
```

缺任何一个会报：`required challenge artifact does not exist: /root/archive/bin/vaultsvc.exe`

---

## 1. 关于 30 分钟自动重启（`--timeout`）

`run.py` 现在是一个**死循环**：每轮启动一台全新 qemu（`snapshot=on`，客户机
磁盘改动全部丢弃），用同一套账号/flag 重新 provisioning，跑 `--timeout` 秒，
到点后关掉这一轮 qemu、立刻开始下一轮——如此往复，**进程不会自己退出**。

所以 `--timeout` 的含义 = **每轮运行多久后自动重启一次**。`vs.json` 里
`timeout=1800` 即 **每 30 分钟重启一次**，每次都是干净客户机，账号 / 密码 /
flag 保持不变（都从 `vs.json` 读，跨轮不变）。

要改间隔：编辑 `vs.json` 里每个条目的 `"timeout"` 字段（单位秒），然后重启该
实例。常用值：30 分钟 `1800`，1 小时 `3600`，2 小时 `7200`。

> 8 台实例是同时启动的，所以 30 分钟到点也几乎同时到，会有一波约 1.5–2 分钟
> 的"全 8 台同时重启"窗口（Windows 开机 + provisioning）。这是正常的；玩家断开
> 重连即可。

---

## 2. 启动（全部 8 台）

```bash
tmux new-session -d -s babycom \
  'cd /root/babycom && python3 -u multirun.py /root/babycom/vs.json'
```

## 3. 查看状态

```bash
tmux ls                                            # session 是否存在
tmux capture-pane -t babycom -p | tail -40        # 启动日志（含每台密码/flag）
ss -ltnp | grep -E ':2830[0-7]'                    # 8 个端口应都在 LISTEN
ps -eo args | grep qemu-system-x86_64 | grep -v android   # 应有 8 个 qemu
tail -f /tmp/logs/28300.log                        # 单台 qemu 日志
```

查看某台的玩家密码（从配置里读）：

```bash
python3 -c "import json;[print(e['ssh_port'],e['user_password']) for e in json.load(open('/root/babycom/vs.json'))]"
```

## 4. 关闭

全部 8 台：

```bash
tmux kill-session -t babycom
pkill -f '[f]ile=/root/babycom/babycom.qcow2' 2>/dev/null || true   # 清残留 qemu
```

单台（例 28303）：

```bash
tmux kill-session -t bc-28303 2>/dev/null || true
pkill -f '[r]un.py --ssh-port 28303' 2>/dev/null || true
```

## 5. 重启

> 平时**不需要手动重启**——`run.py` 每 30 分钟（`timeout`）自动重启每台实例。
> 只有改了 `vs.json`（flag / 密码 / 端口 / 间隔）或某台卡住时才需要手动重启。

全部 8 台 = 先关后开：

```bash
tmux kill-session -t babycom 2>/dev/null
pkill -f '[f]ile=/root/babycom/babycom.qcow2' 2>/dev/null || true
sleep 3
tmux new-session -d -s babycom \
  'cd /root/babycom && python3 -u multirun.py /root/babycom/vs.json'
```

单台（用 `run_one.sh` 从 `vs.json` 读该端口参数，例 28303）：

```bash
tmux kill-session -t bc-28303 2>/dev/null
pkill -f '[r]un.py --ssh-port 28303' 2>/dev/null || true
sleep 2
tmux new-session -d -s bc-28303 '/root/babycom/run_one.sh 28303'
```

## 6. 改 flag / 密码 / 端口

改 `vs.json` 对应字段（`flag` / `ssh_port` / `user_password` / `admin_password` / `timeout`），
然后「重启全部」或「重启单台」。玩家密码是每台独立的 `user_password`。
