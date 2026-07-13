# someday

- **Category:** Pwn
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

The goal of this challenge is to escalate to SYSTEM on a Windows guest and read
the flag at `\\.\PhysicalDrive1`. A patched `vhdmp.sys` kernel driver is provided
for the player; players are advised to load it in VMware or Hyper-V and work on
it locally.

For convenience, a directory at `C:\Users\Public\tmp` has been created and
excluded from Windows Defender scans, so players can run their exploit without
needing to bypass Windows Defender.

The flag is injected into each guest at boot as a raw secondary IDE disk
(`flag-drive.raw` built by `run.py`), which is what shows up as
`\\.\PhysicalDrive1`. Instances auto-restart every 30 minutes (`timeout=1800`
in `wk.json`) with a fresh snapshot — accounts and flag stay the same across
restarts.

### Connection info

- Address: `vm.ctf2026.r3kapig.com:28400-28415`
- User: `hacker`
- Password: `hacker123@`

If you have any issues with the challenge environment, please open a ticket on
Discord.

## Files

- `attachment/vhdmp.sys` — the patched kernel driver for players; load it in
  VMware or Hyper-V to work on the challenge locally (~1 MB).
- `run.py` — per-instance launcher: boots one QEMU Windows guest, provisions
  the `hacker` account and `C:\Users\Public\tmp`, attaches the flag disk, and
  loops with fresh snapshots every `timeout` seconds.
- `multirun.py` — launches all instances from a JSON config, staggered 6 s
  apart to avoid boot I/O spikes.
- `run_one.sh` — restarts a single instance by port, reading its parameters
  from `wk.json`.
- `run_example.py` / `multirun_example.py` — config examples for `run.py` /
  `multirun.py`.
- `OPS.md` — full ops runbook (start / stop / restart / status, per-port admin
  passwords, how to change flag or passwords).

## Deployment

This challenge is **not** a Docker image — it runs as 16 QEMU/KVM instances
directly on the VM host (`vm.ctf2026.r3kapig.com`), managed by the ops scripts
here. The guest image (`/root/someday/ctf.qcow2`) and instance config
(`/root/someday/wk.json`) live on the host, not in git. Instances run inside a
tmux session named `someday`; per-port qemu logs go to `/tmp/logs/<port>.log`.

Start all instances:

```sh
tmux new-session -d -s someday \
  'cd /root/someday && python3 -u multirun.py /root/someday/wk.json'
```

- **Ports:** 28400–28415 (one SSH per instance)
- **Flag:** `r3ctf{pwn2own_for_the_win!!!!!!!}` (static, same for all
  instances; passed to `run.py --flag` from `wk.json` and written to the
  per-instance flag disk at boot)

See **`OPS.md`** for the full runbook.
