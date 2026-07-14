# z3kapig

- **Author:** Giapppp
- **Submissions:** 30
- **Solves:** 25

## Description

Not sure this challenge is focus on ZKP or not, but i think the challenge name is cool!

A Python crypto service implementing the CGGMP21 threshold-ECDSA protocol
(`ecdsa/` keygen/presigning/signing with ZK proofs in `crypto/zkp/`), exposed
over `socat` behind a proof-of-work gate. The flag lives in `flag.txt` inside
the container and is read by the service; the intended solve is the malicious
CGGMP21 flow (see `solve/`, which recovers the flag via an LLL/CVP attack).

## Files

- `attachment/` — player handout: the protocol source (`crypto/`, `ecdsa/`,
  `main.py`, `party.py`, `proof_of_work.py`, `requirements.txt`), without the
  flag.
- `deploy/` — the live service: `src/` (same source + `flag.txt` placeholder),
  `Dockerfile`, `entrypoint.sh`, `run.sh`, `docker-compose.yml`, `.env`.
- `solve/` — reference solver (`solve.py` + `lll_cvp.py`); needs sage + pwntools
  + sympy + the protocol source, and extracts the flag via the malicious CGGMP21
  flow.
- `infra.sh` — build + run script (run from inside `deploy/`).
- `README.md` — this file.

## Deployment

Python service over `socat`, gated by a proof-of-work (`POW_DIFFICULTY=26`,
`PROTOCOL_TIMEOUT_SECONDS=600`). Dynamic flag: `entrypoint.sh` writes `$FLAG`
to `src/flag.txt` at runtime (falling back to the committed
`r3ctf{TEST_Dynamic_FLAG}` placeholder), then scrubs the env.

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/z3kapig:latest`
- **Port:** container `1337` (socat), host `1338`
- **Flag env:** `FLAG`
- **Flag:** `r3ctf{people_should_move_to_better_one_than_cggmp21...}`
