# rECp1cG

- **Category:** Crypto
- **Author:** 
- **Points:** 
- **Solves:** 

## Description

A Coppersmith-style crypto challenge. Connect to the TCP service, solve the
challenge, and recover the flag.

## Deployment

The flag is injected via the `FLAG` environment variable at runtime (read by
`secret.py`); only a placeholder lives in `deploy/`.

```sh
cd deploy && ../infra.sh
```

## Files

- `deploy/` — the live TCP service (`challenge.py` + `secret.py`, served via
  `socat` on port 9999).
