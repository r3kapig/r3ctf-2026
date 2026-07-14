# r3ticket

- **Author:** Giapppp
- **Submissions:** 138
- **Solves:** 101

## Description

Another ticket challenge!

A Python crypto service served over `socat`. The service holds 128 random
16-bit numbers and answers one Lagrange-interpolation query at a player-chosen
index. It then runs 16 rounds: each round it picks a random 24-bit exponent
`x`, computes `h = Σ num_i^x` as a high-precision `mpfr` value, and reveals
the leading 64 decimal digits. The player must reply with the correct `x`
within 3 seconds per round. Winning all 16 rounds prints the flag from
`flag.txt`.

The intended solve uses the single interpolation query (evaluating the
polynomial far outside `[0, 127]` via a huge negative index) to recover all
128 numbers, then matches each round's leading digits against the recovered
numbers to derive `x`. The reference solver uses SageMath (modular recovery
over several primes) plus pwntools.

## Files

- `attachment/chall.py` — player handout (the challenge source).
- `deploy/` — the live service: `chall.py`, `Dockerfile`, `entrypoint.sh`
  (dynamic flag injection), `run.sh` (socat exec target), `requirements.txt`
  (`gmpy2`), `docker-compose.yml`, `flag.txt` (committed placeholder).
- `infra.sh` — build + run script (run from inside `deploy/`).
- `solve/solve.py` — reference solver (SageMath + pwntools; connects to the
  service and extracts the flag).

## Deployment

Python service over `socat` (`python:3.12-slim` base). Dynamic flag: the
platform injects the per-team flag via `$FLAG`; `entrypoint.sh` writes it to
`/home/ctf/flag.txt` (mode `0400`) and scrubs the env, falling back to a
placeholder for local runs.

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3ticket:latest`
- **Port:** container `1337` (socat, `-T 180` timeout), host `1337`
  (compose override: `R3TICKET_PORT`)
- **Flag env:** `FLAG`
- **Resources:** 1 CPU, 512 MB RAM
- **Flag:** `r3ctf{hope_you_love_this_ticket_series_xD}` (static answer)
