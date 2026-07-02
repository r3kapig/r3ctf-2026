# winkernel

- **Category:** Pwn
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

A Windows kernel pwn challenge (a `ctf.qcow2` guest). Players SSH into a
per-instance VM as `hacker` and exploit the in-guest kernel driver to read the
flag.

## Deployment

This challenge is **not** a Docker image and has no player attachment in this
repo — it runs as 8 QEMU/KVM instances directly on the VM host
(`vm.ctf2026.r3kapig.com`), managed by the ops scripts here. The guest image
(`ctf.qcow2`) and instance config (`wk.json`) live on the host (not in git).

- **Ports:** 28400–28407 (one SSH per instance)
- **Flag:** `r3ctf{1d5757f5-ee23-487b-bcd5-b4319265792e}` (static, same for all)
- **Files in this repo:** `run.py` (per-instance launcher), `multirun.py`
  (launch all 8), `run_one.sh` (restart one), `run_example.py` /
  `multirun_example.py` (config examples), and `OPS.md`.

See **`OPS.md`** for the full runbook (start / stop / restart / status / change
flag or passwords).
