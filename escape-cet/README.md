# Escape CET

- **Category:** Pwn
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

> Crazyman was sitting in the CET-4 exam room, staring at a passage that made less sense the longer he read it.
>
> The listening section had ended. The invigilator said nothing. The clock stopped moving.
>
> Then the answer sheet folded itself into a narrow stone tablet, and the classroom lights stretched into a ruined ford beneath a moonless sky. Three relics waited where the river forgot its name:
>
> A ring that cuts one truth into stone,
> A slab that remembers every mark,
> A bridge that answers only when crossed.
>
> Somewhere in this place, a secret is hidden. Crazyman is told that only those who understand the strange rules of CET may return.
>
> The tablet glimmers with an address.
> The bridge hums under a silent examiner.
> The Silent Dream Examiner watches every step across the bridge.
> Some lines on the sheet have been erased by a careful filter; the missing words may matter more than the ones left behind.
> And deep below the stones, something is still being simulated.
>
> Find the secret. Then leave the exam.

A CET (Control-flow Enforcement Technology) pwn. Players connect to a service
that runs the `tcet` binary under Intel SDE (Software Development Emulator) with
CET enforced, and exploit it to read the flag.

## Attachment

`attachment/attachment.zip` — player handout: `pwn` (the challenge binary),
`libc.so.6`, `ld-linux-x86-64.so.2`.

## Deployment

Single container (`ubuntu:24.04`). `tdocker-server` listens on TCP **9999**; per
connection it runs the `tcet` binary under Intel SDE with CET enabled
(`-cet 1 -cet-endbr-exe 1`). The flag is injected via the `FLAG` environment
variable (required); `entrypoint.sh` writes it to `/root/flag` (root 0400) and
scrubs the env. (The `/flag` players see is an encrypted decoy produced by
`start.sh`; the real flag is `/root/flag`.)

```sh
docker build -t registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/escape-cet:latest deploy/
# local run:
cd deploy && ../infra.sh
```

Runtime needs no special devices (pure CPU; Intel SDE dynamic instrumentation).
Per-connection CPU is moderate (SDE emulation overhead).

## Files

- `attachment/attachment.zip` — player handout.
- `deploy/` — the live container (`Dockerfile`, `bin/` (`tdocker-server`,
  `drop-exec`, `encryptor`), `challenge/` (`tcet`, `libc.so.6`,
  `ld-linux-x86-64.so.2`), `environment/` (Intel SDE), and the
  `entrypoint.sh` / `start.sh` / `run_challenge.sh` scripts).
