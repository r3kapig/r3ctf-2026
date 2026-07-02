# eazyvpn

- **Category:** Pwn
- **Author:** Squeasp
- **Difficulty:** Easy
- **Wave:** 2
- **Points:** 
- **Solves:** 

## Description

simple sslvpn... but something more.

SSL VPN inspired by a Fortinet exploit + heap fengshui. Pwn the `fw_ctf_host` binary,
then pivot through the VPN into the internal `172.20.0.0/24` network to reach the
flag service.

## Deployment

The flag is injected via `$FLAG` (also `$GZCTF_FLAG` / `$DASFLAG`) at runtime;
`entrypoint.sh` writes it to `/flag` and `/app/flag` then scrubs the env. Only a
placeholder is committed.

```sh
cd deploy && ../infra.sh
```

## Files

- `attachment/` — player handout (`fw_ctf_host` binary + its `lib/`).
- `deploy/` — the live container (vpn gateway + internal decoy/flag services).
