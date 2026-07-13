# BabyCOM

- **Category:** Pwn
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

Vault service, the place where your data is kept secret.

A Windows exploitation challenge built around a vulnerable COM service
(`VaultSvc`, CLSID `{1B2C3D4E-5F67-8901-A234-56789BCDEF01}`) running inside a
Windows Server 2025 Standard 24H2 (build 26100.32995) guest. Players receive the
service artifacts and a QCOW2 image, log in as the low-privileged `hacker`
user, and must abuse the COM service to read the flag from the guest's second
virtual disk — flag location: `\\.\PhysicalDrive1`. The intended solve extracts
the flag through the service **without** achieving code execution.

**Solve locally first:** download the QCOW2 image, log in, change the `hacker`
user's password to one of your choosing, and run your exploit to get the flag.
Once solved locally, open a ticket on Discord to receive the SSH connection
details for the remote machine.

VM configuration (local / remote instance):

- 1 vCPU core / 512MB memory
- **QCOW2 image:**
  - [Google Drive](https://drive.google.com/file/d/1QpTdwUSVAiLo1FnJUPAh_n9lHgfUTV18/view?usp=drive_link)
  - [Baidu Pan](https://pan.baidu.com/s/1FY03ijKs-f0EQB9vRoDCIg?pwd=R326)
- **Administrator password:** `!R3k4CtF_4DM1n!`

## Files

- `attachment/` — player handout: the COM-service artifacts (`vaultsvc.exe`,
  `vaultsvc.idl`, `vaultsvc.tlb`, `vaultsvc_ps.dll`) plus `windows-version.txt`
  (guest OS build info).
- `artifacts/` — the same COM-service artifacts, staged for copying to
  `/root/archive/bin/` on the host before launch (see `OPS.md` §0).
- `run.py` — per-instance QEMU launcher: boots a fresh snapshot guest,
  provisions the account/flag, exposes one SSH port, and auto-restarts on a
  timeout cycle.
- `multirun.py` — launches all 16 instances from the config with a staggered
  start; `run_one.sh` — restart a single instance by SSH port.
- `run_example.py` / `multirun_example.py` — config examples.
- `OPS.md` — full ops runbook (start / stop / restart / status / change flag or
  passwords; current per-instance player credentials).

## Deployment

This challenge is **not** a Docker image — it runs as 16 QEMU/KVM Windows
instances directly on the VM host (`vm.ctf2026.r3kapig.com`), managed by the
ops scripts here. The guest image (`babycom.qcow2`) and instance config
(`vs.json`) live on the host (not in git); per-instance flag, passwords, SSH
port, and timeout are read from `vs.json`.

- **Ports:** 28300–28315 (one SSH per instance, user `hacker` with a
  per-instance random password from `vs.json`)
- **Flag:** `r3ctf{intended-flag-extraction-without-code-exec}` (static, same
  for all instances; injected onto the guest's flag disk at provisioning)

Start all instances on the host:

```sh
tmux new-session -d -s babycom \
  'cd /root/babycom && python3 -u multirun.py /root/babycom/vs.json'
```

Instances auto-restart every `timeout` seconds (1800 = 30 min) with a clean
snapshot guest; restarts are staggered so they never fire all at once. See
**`OPS.md`** for the full runbook.
