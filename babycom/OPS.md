# babycom Ops Runbook

- VM image: `/root/babycom/babycom.qcow2`
- Instance config: `/root/babycom/vs.json` (16 instances, ports 28300–28315)
- Player account: `hacker` / `<per-instance random password>` (see the `user_password` field in `vs.json`)
- Flag: `r3ctf{intended-flag-extraction-without-code-exec}` (same for all instances)
- tmux session: `babycom`
- Logs: `/tmp/logs/<port>.log`

---

## Current instance credentials (port / account / password)

From `/root/babycom/vs.json` — the player credentials for the **current** deployment.
Passwords change every time `vs.json` is regenerated; re-read them with the command
in section 3 and update this table.

| Port | Account | Password | Connect |
|---|---|---|---|
| 28300 | `hacker` | `VU0!28287750d2360b4d9` | `ssh -p 28300 hacker@vm.ctf2026.r3kapig.com` |
| 28301 | `hacker` | `VU1!5726795ad027e0639` | `ssh -p 28301 hacker@vm.ctf2026.r3kapig.com` |
| 28302 | `hacker` | `VU2!9503ae2718e421e49` | `ssh -p 28302 hacker@vm.ctf2026.r3kapig.com` |
| 28303 | `hacker` | `VU3!1c673e17326cb3b09` | `ssh -p 28303 hacker@vm.ctf2026.r3kapig.com` |
| 28304 | `hacker` | `VU4!80fa052d4106f1ad9` | `ssh -p 28304 hacker@vm.ctf2026.r3kapig.com` |
| 28305 | `hacker` | `VU5!a19e1ecca68658779` | `ssh -p 28305 hacker@vm.ctf2026.r3kapig.com` |
| 28306 | `hacker` | `VU6!82cb72596348d0b69` | `ssh -p 28306 hacker@vm.ctf2026.r3kapig.com` |
| 28307 | `hacker` | `VU7!0c6032e7f599c11b9` | `ssh -p 28307 hacker@vm.ctf2026.r3kapig.com` |
| 28308 | `hacker` | `VU8!8a179d323cb6ad7cb` | `ssh -p 28308 hacker@vm.ctf2026.r3kapig.com` |
| 28309 | `hacker` | `VU9!5307e842a802c4ef2` | `ssh -p 28309 hacker@vm.ctf2026.r3kapig.com` |
| 28310 | `hacker` | `VU10!e21065fe67a4fc0fe` | `ssh -p 28310 hacker@vm.ctf2026.r3kapig.com` |
| 28311 | `hacker` | `VU11!71e0406f1f2db054c` | `ssh -p 28311 hacker@vm.ctf2026.r3kapig.com` |
| 28312 | `hacker` | `VU12!292a8b61365c64408` | `ssh -p 28312 hacker@vm.ctf2026.r3kapig.com` |
| 28313 | `hacker` | `VU13!44dda69a0ff704b72` | `ssh -p 28313 hacker@vm.ctf2026.r3kapig.com` |
| 28314 | `hacker` | `VU14!9b3f651b5697499f3` | `ssh -p 28314 hacker@vm.ctf2026.r3kapig.com` |
| 28315 | `hacker` | `VU15!a01010b87e72e0aab` | `ssh -p 28315 hacker@vm.ctf2026.r3kapig.com` |

Flag (same for all; read inside the guest via the COM service vulnerability):
`r3ctf{intended-flag-extraction-without-code-exec}`

> Players connect from the public internet, so `vm.ctf2026.r3kapig.com` must resolve
> to this VM host and the firewall/security group must allow ports 28300–28315.

---

## 0. Prerequisites (must be in place or startup fails)

Before starting a guest, `run.py` copies 3 COM service files from the host's
`/root/archive/bin/` into the guest:

```
/root/archive/bin/vaultsvc.exe
/root/archive/bin/vaultsvc_ps.dll
/root/archive/bin/vaultsvc.tlb
```

If any is missing: `required challenge artifact does not exist: /root/archive/bin/vaultsvc.exe`

---

## 1. The 30-minute auto-restart (`--timeout`)

`run.py` is an **infinite loop**: each round boots a fresh qemu (`snapshot=on`, all
guest disk changes discarded), re-provisions with the same account/flag, runs for
`--timeout` seconds, then kills that round's qemu and immediately starts the next
round — the process never exits on its own.

So `--timeout` = **how long each round runs before an auto-restart**. `timeout=1800`
in `vs.json` means **restart every 30 minutes**, always with a clean guest; account /
password / flag stay the same (read from `vs.json`, stable across rounds).

To change the interval: edit the `"timeout"` field (seconds) of each entry in
`vs.json`, then restart that instance. Common values: 30 min `1800`, 1 h `3600`, 2 h `7200`.

> **Staggered restarts**: `run.py`'s **first** round lasts `random(0, timeout)` seconds,
> so the first restart (and every 30-minute restart after it) spreads uniformly across
> the 30-minute window — **the 16 instances never all restart at once**. In steady
> state roughly one instance restarts every ~2 minutes (each restart is ~1.5–2 min of
> downtime; players just reconnect). `multirun.py` also adds a 6-second gap between
> instances at startup to avoid the I/O / CPU spike of 16 Windows VMs powering on
> simultaneously.
>
> Note: because the first round is `random(0, timeout)`, some instances may have a
> very short first round (tens of seconds) and restart soon after startup — this is
> expected; afterwards they settle into the stable 30-minute cycle.

---

## 2. Start (all 16 instances)

```bash
tmux new-session -d -s babycom \
  'cd /root/babycom && python3 -u multirun.py /root/babycom/vs.json'
```

## 3. Status

```bash
tmux ls                                            # does the session exist
tmux capture-pane -t babycom -p | tail -40        # startup log (incl. per-instance password/flag)
ss -ltnp | grep -E ':283(0[0-9]|1[0-5])'       # all 16 ports should be LISTEN
ps -eo args | grep qemu-system-x86_64 | grep -v android   # should show 16 qemu processes
tail -f /tmp/logs/28300.log                        # single-instance qemu log
```

Read an instance's player password from the config:

```bash
python3 -c "import json;[print(e['ssh_port'],e['user_password']) for e in json.load(open('/root/babycom/vs.json'))]"
```

## 4. Stop

All 16 instances:

```bash
tmux kill-session -t babycom
pkill -f '[f]ile=/root/babycom/babycom.qcow2' 2>/dev/null || true   # clean up leftover qemu
```

Single instance (e.g. 28303):

```bash
tmux kill-session -t bc-28303 2>/dev/null || true
pkill -f '[r]un.py --ssh-port 28303' 2>/dev/null || true
```

## 5. Restart

> Manual restarts are **not normally needed** — `run.py` auto-restarts each instance
> every 30 minutes (`timeout`). Only restart manually after changing `vs.json`
> (flag / password / port / interval) or when an instance is stuck.

All 16 instances = stop then start:

```bash
tmux kill-session -t babycom 2>/dev/null
pkill -f '[f]ile=/root/babycom/babycom.qcow2' 2>/dev/null || true
sleep 3
tmux new-session -d -s babycom \
  'cd /root/babycom && python3 -u multirun.py /root/babycom/vs.json'
```

Single instance (`run_one.sh` reads that port's parameters from `vs.json`; e.g. 28303):

```bash
tmux kill-session -t bc-28303 2>/dev/null
pkill -f '[r]un.py --ssh-port 28303' 2>/dev/null || true
sleep 2
tmux new-session -d -s bc-28303 '/root/babycom/run_one.sh 28303'
```

## 6. Change flag / password / port

Edit the corresponding fields in `vs.json` (`flag` / `ssh_port` / `user_password` /
`admin_password` / `timeout`), then "restart all" or "restart single". The player
password is the per-instance `user_password`.
