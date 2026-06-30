# fw-vpn

- **Category:** Misc
- **Author:** 
- **Points:** 
- **Solves:** 

## Description

FW-CTF v1.0 — an SSL VPN gateway. Connect over TLS, authenticate, then tunnel via
SOCKS5 CONNECT into the private `172.20.0.0/24` network to reach the internal flag
service. Write a special client to pivot through the VPN and grab the flag.

## Hints

- The binary speaks TLS then a SOCKS5-like CONNECT relay.

## Deployment

The real flag is injected via the `FLAG` environment variable at runtime into the
internal `api` service; only a placeholder lives in `deploy/flag`. The hardcoded
`R3CTF{...}` string in the binary is a decoy.

```sh
cd deploy/docker && docker compose up -d
```

## Files

- `attachment/` — public handout (`fw_ctf_host` binary).
- `deploy/` — the live multi-service container stack.
