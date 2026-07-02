# R3CTF 2026

Source code and deployment material for the R3CTF 2026 challenges.

This is the `infra` branch, holding the dynamic-challenge build / deploy sources.

## Challenges

| Category | Challenge | Image |
|---|---|---|
| Crypto | HEuristic | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/heuristic:latest` |
| Crypto | rECp1cG | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/recp1cg:latest` |
| Pwn | eazyvpn | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/eazyvpn:latest` |
| Misc | netshare | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest` |
| Misc | trustedhash | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/trustedhash:latest` |
| Pwn | pewpew | (static attachment) |
| Misc | Time Capsule | (static attachment) |
| Pwn | whisper | (local run only) |
| Crypto | teRRibleRing | (static attachment) |
| Pwn | r3map | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3map:latest` |
| Pwn | P1gROXY | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/p1groxy:latest` |

See [`CHALLENGE.md`](./CHALLENGE.md) for the full list with CPU / memory limits and
deploy notes.

## Layout

Each challenge follows the r3ctf convention:

```text
<Category>/<challenge>/
├── README.md
├── infra.sh
├── attachment/   # public handout (large artifacts are hosted externally)
└── deploy/       # live container / infra
```

## Large artifacts

Files over GitHub's 100MB limit are **not** stored in the repo (see `.gitignore`):

- `Pwn/whisper/attachment/whisper-local-stack.7z`
- `Misc/Time Capsule/attachment/satellitelog/Satellite_log--2A7E.4.003.pcap`

They are distributed via the contest platform / object storage.
