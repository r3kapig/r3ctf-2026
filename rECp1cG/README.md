# rECp1cG

- **Category:** Crypto
- **Author:** deebato
- **Difficulty:** Medium/Hard
- **Wave:** 2
- **Points:**
- **Solves:**

## Description

Quiet steps, old notes:

https://eprint.iacr.org/2007/099.pdf

ECLCG / ECHNP.

## Files

- `attachment/challenge.py` — player handout (the challenge script).
- `deploy/` — the live TCP service (`challenge.py` + `secret.py`, served via
  `socat` on port 9999).

## Deployment

The flag is injected via the `FLAG` environment variable at runtime (read by
`secret.py`); only a placeholder lives in `deploy/`.

```sh
cd deploy && ../infra.sh
```
