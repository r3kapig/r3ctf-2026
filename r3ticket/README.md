# r3ticket

- **Category:** Crypto
- **Author:** Giapppp
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

Another ticket challenge!

## Files

- `attachment/chall.py` — player handout (the challenge source).
- `deploy/` — the live service: `chall.py`, `Dockerfile`, `entrypoint.sh`,
  `run.sh`, `requirements.txt`, `docker-compose.yml`.

## Deployment

Python service over `socat`. The flag is injected at runtime via `$FLAG`
(`entrypoint.sh` writes it to `flag.txt`, then scrubs the env); a placeholder is
committed in `deploy/flag.txt`.

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3ticket:latest`
- **Port:** container `1337` (socat), host `1337`
- **Flag env:** `FLAG`

## Flag (static answer)

```
r3ctf{hope_you_love_this_ticket_series_xD}
```
