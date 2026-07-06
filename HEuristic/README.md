# HEuristic

- **Category:** Crypto
- **Author:** dengfeng
- **Difficulty:** Easy
- **Wave:** 3
- **Points:** 
- **Solves:** 

## Description

HE is HEuristic

FHE / HNP / LLL. A heuristic homomorphic-encryption service built on Microsoft SEAL
(CKKS). Recover the secret scale `delta` using a limited number of encrypt/decrypt
oracle rounds, then submit `delta mod q` to get the flag.

## Hints

- You get only 3 rounds. The decrypt oracle adds per-coefficient noise and masks
  high indices.

## Deployment

The flag is injected via the `FLAG` environment variable at runtime and read by the
service with `getenv("FLAG")`; it is printed only when you submit the correct `delta`.

```sh
cd deploy && ../infra.sh
```

## Files

- `attachment/` — player handout: `server.cc`, `CMakeLists.txt`, and `run.sh`
  (build script; clones Microsoft SEAL and builds `he_server` locally).
- `deploy/` — the live container (SEAL + `he_server` behind `socat` on port 9999).
