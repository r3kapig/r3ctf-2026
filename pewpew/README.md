# pewpew

- **Category:** Pwn
- **Author:** sub1s
- **Difficulty:** Easy
- **Wave:** 1
- **Points:** 
- **Solves:** 

## Description

The spaceship is making noises again.

Management says this is normal. Engineering says not to press the red buttons. The
flight computer says everything is perfectly calibrated.

Have fun.

Windows LFH playground. Connect to the remote Windows host (Windows Server 2025) and
find the flag. A Remote Desktop connection file is provided in `attachment/`.

## Connection

- Open `attachment/r3ctf-pewpew.rdp` (or any RDP client) and connect to the host
  recorded inside it.
- The username is embedded in the file; the password is distributed separately by
  the platform.

## Deployment

This challenge points at an externally-hosted Windows VM; there is no local
container to build. The `.rdp` file in `attachment/` is the full player handout.

## Files

- `attachment/r3ctf-pewpew.rdp` — RDP connection stub for players.
