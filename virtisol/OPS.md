# virtisol 运维指南

- 题目镜像: `/root/virtisol/babycom.qcow2`
- 实例配置: `/root/virtisol/vs.json`（8 个实例，端口 28300–28307）
- 玩家账号: `hacker` / `<每台随机密码>`（密码见 `vs.json` 的 `user_password` 字段）
- flag: `r3ctf{8d9c9e48-2b4e-404d-9666-d015c707576c}`（全题同一个）
- tmux session: `virtisol`
- 日志: `/tmp/logs/<port>.log`

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

## 1. 关于 lifetime（`--timeout`）

每个 `run.py` 启动时带一个 `--timeout <秒>`。它会 `sleep` 这么久，然后
**自动关停 qemu + 代理并清理临时目录**。`vs.json` 里 `timeout=86400` 即
**启动 24h 后该实例自动退出**。

要改时长：编辑 `vs.json` 里每个条目的 `"timeout"` 字段（单位秒），然后重启。
常用值：3 天 `259200`，7 天 `604800`，30 天 `2592000`。

---

## 2. 启动（全部 8 台）

```bash
tmux new-session -d -s virtisol \
  'cd /root/virtisol && python3 -u multirun.py /root/virtisol/vs.json'
```

## 3. 查看状态

```bash
tmux ls                                            # session 是否存在
tmux capture-pane -t virtisol -p | tail -40        # 启动日志（含每台密码/flag）
ss -ltnp | grep -E ':2830[0-7]'                    # 8 个端口应都在 LISTEN
ps -eo args | grep qemu-system-x86_64 | grep -v android   # 应有 8 个 qemu
tail -f /tmp/logs/28300.log                        # 单台 qemu 日志
```

查看某台的玩家密码（从配置里读）：

```bash
python3 -c "import json;[print(e['ssh_port'],e['user_password']) for e in json.load(open('/root/virtisol/vs.json'))]"
```

## 4. 关闭

全部 8 台：

```bash
tmux kill-session -t virtisol
pkill -f '[f]ile=/root/virtisol/babycom.qcow2' 2>/dev/null || true   # 清残留 qemu
```

单台（例 28303）：

```bash
tmux kill-session -t vs-28303 2>/dev/null || true
pkill -f '[r]un.py --ssh-port 28303' 2>/dev/null || true
```

## 5. 重启

全部 8 台 = 先关后开：

```bash
tmux kill-session -t virtisol 2>/dev/null
pkill -f '[f]ile=/root/virtisol/babycom.qcow2' 2>/dev/null || true
sleep 3
tmux new-session -d -s virtisol \
  'cd /root/virtisol && python3 -u multirun.py /root/virtisol/vs.json'
```

单台（用 `run_one.sh` 从 `vs.json` 读该端口参数，例 28303）：

```bash
tmux kill-session -t vs-28303 2>/dev/null
pkill -f '[r]un.py --ssh-port 28303' 2>/dev/null || true
sleep 2
tmux new-session -d -s vs-28303 '/root/virtisol/run_one.sh 28303'
```

## 6. 改 flag / 密码 / 端口

改 `vs.json` 对应字段（`flag` / `ssh_port` / `user_password` / `admin_password` / `timeout`），
然后「重启全部」或「重启单台」。玩家密码是每台独立的 `user_password`。
