# someday Ops Guide

- Challenge image: `/root/someday/ctf.qcow2`
- Instance config: `/root/someday/wk.json` (16 instances, ports 28400–28415)
- Player account: `hacker` / `hacker123@` (hardcoded in `run.py`, shared by all instances)
- Flag: `r3ctf{pwn2own_for_the_win!!!!!!!}` (same for the whole challenge)
- tmux session: `someday`
- Logs: `/tmp/logs/<port>.log`

---

## Deployed instances (port / account / admin password)

Player password is `hacker123@` for all. Admin passwords come from `/root/someday/wk.json`, one per instance:

| Port | Account | Player password | Admin password | Connect command |
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

Flag (same for the whole challenge): `r3ctf{pwn2own_for_the_win!!!!!!!}`

> Public player access requires `vm.ctf2026.r3kapig.com` DNS pointing at this VM host
> and the firewall/security group allowing ports 28400–28415.

---

## 0. The 30-minute auto-restart (`--timeout`)

`run.py` is an **infinite loop**: each round boots a fresh qemu (`snapshot=on`, guest
disk changes discarded), re-provisions the same accounts/flag, runs for `--timeout`
seconds, then kills that round's qemu and immediately starts the next — **the process
never exits on its own**.

So `--timeout` = **how long each round runs before an automatic restart**. `timeout=1800`
in `wk.json` means **restart every 30 minutes**, always with a clean guest; accounts /
passwords / flag stay the same (all read from `wk.json`, constant across rounds).

To change the interval: edit the `"timeout"` field (seconds) of each entry in `wk.json`,
then restart that instance. Common values: 30 min `1800`, 1 hour `3600`, 2 hours `7200`.

> **Staggered restarts**: `run.py`'s **first** round lasts `random(0, timeout)` (uniform),
> so the "first restart" (and every 30-minute restart after it) is spread evenly across
> the 30-minute window — **all 16 never restart at once**. In steady state roughly one
> instance restarts every ~2 minutes (each ~1.5–2 minutes of downtime; players just
> reconnect). `multirun.py` also adds a 6-second gap between instances at startup to
> avoid the I/O / CPU spike of 16 Windows guests powering on simultaneously.
>
> Note: because the first round is `random(0, timeout)`, some instances' first round may
> be very short (tens of seconds) and restart soon after boot — expected behavior; after
> that they settle into the steady 30-minute cycle.

---

## 1. Start (all instances)

```bash
tmux new-session -d -s someday \
  'cd /root/someday && python3 -u multirun.py /root/someday/wk.json'
```

## 2. Status

```bash
tmux ls                                            # session exists?
tmux capture-pane -t someday -p | tail -40       # startup log (incl. per-instance password/flag)
ss -ltnp | grep -E ':284(0[0-9]|1[0-5])'       # all 16 ports should be LISTEN
ps -eo args | grep qemu-system-x86_64 | grep -v android   # should show 16 qemu processes
tail -f /tmp/logs/28400.log                        # single-instance qemu log
```

Verify external reachability of one instance:

```bash
ssh -p 28403 hacker@vm.ctf2026.r3kapig.com      # password hacker123@
```

## 3. Stop

All instances:

```bash
tmux kill-session -t someday
pkill -f '[f]ile=/root/someday/ctf.qcow2' 2>/dev/null || true   # clean up leftover qemu
```

Single instance (example 28403):

```bash
tmux kill-session -t sd-28403 2>/dev/null || true
pkill -f '[r]un.py --ssh-port 28403' 2>/dev/null || true
```

## 4. Restart

> Manual restarts are **not normally needed** — `run.py` auto-restarts every instance
> every 30 minutes (`timeout`). Only restart manually after changing `wk.json`
> (flag / password / port / interval) or when an instance is stuck.

All instances = stop then start:

```bash
tmux kill-session -t someday 2>/dev/null
pkill -f '[f]ile=/root/someday/ctf.qcow2' 2>/dev/null || true
sleep 3
tmux new-session -d -s someday \
  'cd /root/someday && python3 -u multirun.py /root/someday/wk.json'
```

Single instance (`run_one.sh` reads that port's params from `wk.json`; example 28403):

```bash
tmux kill-session -t sd-28403 2>/dev/null
pkill -f '[r]un.py --ssh-port 28403' 2>/dev/null || true
sleep 2
tmux new-session -d -s sd-28403 '/root/someday/run_one.sh 28403'
```

## 5. Changing flag / passwords / ports

- Flag / ports / admin passwords: edit the corresponding fields in `wk.json`, then
  restart all.
- Player password: not in `wk.json` — it's `HACKER_PASSWORD = "hacker123@"` at the top
  of `run.py`; edit `run.py` and restart all to change it.
