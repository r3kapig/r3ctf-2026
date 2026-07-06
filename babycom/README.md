# BabyCOM

- **Category:** Pwn
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

Vault service, the place where your data is kept secret.

Flag location: `\\.\PhysicalDrive1`

### VM Configuration
- 1 vCPU core / 512MB memory
- **QCOW2 image:** 
  - [Google Drive](https://drive.google.com/file/d/1QpTdwUSVAiLo1FnJUPAh_n9lHgfUTV18/view?usp=drive_link)
  - [Baidu Pan](https://pan.baidu.com/s/1FY03ijKs-f0EQB9vRoDCIg?pwd=R326)
- **Administrator password:** `!R3k4CtF_4DM1n!`

### Solve locally first

Please solve the challenge locally, preferably using the same Windows environment.

Log in to the VM locally and change the `hacker` user's password to one of your choosing. Then run your exploit to get the flag.

Once you have successfully solved the challenge locally, open a ticket on Discord to receive the ssh connection details for the remote machine.

## Files

- `attachment/` — player handout: the COM-service artifacts (`vaultsvc.exe`,
  `vaultsvc.idl`, `vaultsvc.tlb`, `vaultsvc_ps.dll`) plus `windows-version.txt`.
- `artifacts/` — the same COM-service artifacts, copied to `/root/archive/bin/`
  on the host before launch (see `OPS.md` §0).
- `run.py` — per-instance launcher; `multirun.py` — launch all 8 instances;
  `run_one.sh` — restart one instance; `run_example.py` / `multirun_example.py`
  — config examples.
- `OPS.md` — full ops runbook (start / stop / restart / status / change flag or
  passwords).

## Deployment

This challenge is **not** a Docker image — it runs as 8 QEMU/KVM instances
directly on the VM host (`vm.ctf2026.r3kapig.com`), managed by the ops scripts
here. The guest image (`babycom.qcow2`) and instance config (`vs.json`) live on
the host (not in git).

- **Ports:** 28300–28307 (one SSH per instance)
- **Flag:** `r3ctf{intended-flag-extraction-without-code-exec}` (static, same for all)

See **`OPS.md`** for the full runbook.
