# virtisol

- **Category:** Pwn
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

A Windows VM-based pwn challenge (a `babycom.qcow2` guest, COM-service themed).
Players SSH into a per-instance VM as `hacker` and exploit the in-guest service
to read the flag.

## Deployment

This challenge is **not** a Docker image and has no player attachment in this
repo — it runs as 8 QEMU/KVM instances directly on the VM host
(`vm.ctf2026.r3kapig.com`), managed by the ops scripts here. The guest image
(`babycom.qcow2`) and instance config (`vs.json`) live on the host (not in
git). The COM service artifacts (`vaultsvc.exe`, `vaultsvc_ps.dll`,
`vaultsvc.tlb`) are tracked in `artifacts/` and must be copied to
`/root/archive/bin/` on the host before launch (see `OPS.md` §0).

- **Ports:** 28300–28307 (one SSH per instance)
- **Flag:** `r3ctf{8d9c9e48-2b4e-404d-9666-d015c707576c}` (static, same for all)
- **Files in this repo:** `run.py` (per-instance launcher), `multirun.py`
  (launch all 8), `run_one.sh` (restart one), `run_example.py` /
  `multirun_example.py` (config examples), and `OPS.md`.

See **`OPS.md`** for the full runbook (start / stop / restart / status / change
flag or passwords).
