# z3kapig

- **Category:** Crypto
- **Author:** Giapppp
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

Not sure this challenge is focused on ZKP or not, but I think the challenge name
is cool!

A threshold-ECDSA protocol (`cggmp21`-ish, with zero-knowledge proofs) behind a
proof-of-work gate.

## Files

- `attachment/` — player handout: the protocol source (`crypto/`, `ecdsa/`,
  `main.py`, `party.py`, `proof_of_work.py`, `requirements.txt`), without the
  flag.
- `deploy/` — the live service: `src/` (same source + `flag.txt`), `Dockerfile`,
  `entrypoint.sh`, `run.sh`, `docker-compose.yml`.

## Deployment

Python service over `socat`, gated by a proof-of-work (`POW_DIFFICULTY=26`). The
flag is injected at runtime via `$FLAG` (`entrypoint.sh` writes it to
`src/flag.txt`, then scrubs the env); a placeholder is committed in
`deploy/src/flag.txt`.

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/z3kapig:latest`
- **Port:** container `1337` (socat), host `1338`
- **Flag env:** `FLAG`

## Flag (static answer)

```
r3ctf{people_should_move_to_better_one_than_cggmp21...}
```
