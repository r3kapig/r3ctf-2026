# pewpew

- **Category:** Pwn
- **Author:** sub1s
- **Difficulty:** Easy
- **Wave:** 1
- **Points:** 
- **Solves:** 

## Description

The spaceship is making noises again.
Management says this is normal. Engineering says not to press the red buttons. The flight computer says everything is perfectly calibrated.
Have fun.

Challenge running on Windows Server 2025. Reverse the supplied binaries,
then connect to the remote Windows host over port 4444 and find the flag in `flag.txt`.

> You should NOT bruteforce the service; your exploit should be reliable in
> fewer than 10 tries.

Player connection info:

- Address: ```nc pewpew.ctf2026.r3kapig.com 4444```
- You will receive ```team token>```, and you need to enter your team token to get your environment.
- For GUI access, open `attachment/r3ctf-pewpew.rdp` (or any RDP client) and
  connect to the host recorded inside it (`35.215.150.170`, username
  `huangzhengdoc`). The password is distributed separately by the platform.

## Files

- `attachment/` — player handout.
  - `to_player.zip` — `pewpew.exe` plus the Windows DLLs (`KernelBase.dll`,
    `kernel32.dll`, `ntdll.dll`) for local analysis.
  - `r3ctf-pewpew.rdp` — RDP connection stub for the remote host.
- `flag.param.md` — dynamic-flag template + key (platform / checker config).

## Deployment

This challenge points at an externally-hosted Windows VM; there is no local
container to build. The `.rdp` + binaries in `attachment/` are the full player
handout. The flag is dynamic, per the template/key in `flag.param.md`.
