# someday

- **Category:** Pwn
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

The goal of this challenge is to escalate to SYSTEM and read the flag at `\\.\PhysicalDrive1`. A patched vhdmp.sys is provided for the player. Players are advised to use the provided vhdmp.sys, load it in vmware or hyperv and work on it.

For convenience, a directory at `C:\Users\Public\tmp` has been created and excluded from Windows Defender scans, so that players can run their exploit without needing to bypass Windows Defender.

### Connection info:
- Address: vm.ctf2026.r3kapig.com:28400-28415
- User: haker
- Password: hacker123@

If you have any issues with the challenge environment, please open a ticket on Discord.

## Files

- `attachment/vhdmp.sys` — the patched kernel driver for players; load it in
  VMware or Hyper-V to work on the challenge locally (~1 MB).
- `run.py` — per-instance launcher; `multirun.py` — launch all 8 instances;
  `run_one.sh` — restart one instance; `run_example.py` / `multirun_example.py`
  — config examples.
- `OPS.md` — full ops runbook (start / stop / restart / status / change flag or
  passwords).

## Deployment

This challenge is **not** a Docker image — it runs as 8 QEMU/KVM instances
directly on the VM host (`vm.ctf2026.r3kapig.com`), managed by the ops scripts
here. The guest image (`ctf.qcow2`) and instance config (`wk.json`) live on the
host (not in git).

- **Ports:** 28400–28407 (one SSH per instance)
- **Flag:** `r3ctf{pwn2own_for_the_win!!!!!!!}` (static, same for all)

See **`OPS.md`** for the full runbook.
