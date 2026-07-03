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

## Files

- `attachment/to_player.zip` — player handout: `pewpew.exe` plus the Windows
  DLLs (`KernelBase.dll`, `kernel32.dll`, `ntdll.dll`) for local analysis.
- `attachment/r3ctf-pewpew.rdp` — RDP connection stub for the remote host.
- `flag.param.md` — dynamic-flag template + key (platform / checker config).

## Connection

- Open `attachment/r3ctf-pewpew.rdp` (or any RDP client) and connect to the host
  recorded inside it.
- The username is embedded in the file; the password is distributed separately by
  the platform.

## Deployment

This challenge points at an externally-hosted Windows VM; there is no local
container to build. The `.rdp` + binaries in `attachment/` are the full player
handout.
