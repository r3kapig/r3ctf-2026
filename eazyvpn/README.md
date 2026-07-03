# eazyvpn

- **Category:** Pwn
- **Author:** Squeasp
- **Difficulty:** Easy
- **Wave:** 2
- **Points:** 
- **Solves:** 

## Description

simple sslvpn... but something more.

SSL VPN inspired by a Fortinet exploit + heap fengshui. Pwn the `fw_ctf_host` TLS
gateway (listening on :4433) to read the flag at `/flag`.

## Deployment

The flag is injected via `$FLAG` (also `$GZCTF_FLAG` / `$DASFLAG`) at runtime;
`entrypoint.sh` writes it to `/flag` and `/app/flag` then scrubs the env. Only a
placeholder is committed.

```sh
cd deploy && ../infra.sh
```

## Files

- `attachment/` — player handout (`fw_ctf_host` binary + its `lib/`).
- `deploy/` — the live container (the `fw_ctf_host` TLS gateway on :4433; the
  platform-injected flag is written to `/flag` and `/app/flag` by `entrypoint.sh`).
