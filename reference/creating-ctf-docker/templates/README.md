# <Challenge Name>

- **Category:** Web / Pwn / Crypto / Misc / Blockchain / Forensics / Reverse
- **Author:** <handle>
- **Points:** <n>
- **Solves:** <n>

## Description

<Player-facing flavor text: what the challenge is about. This is what appears on the platform.>

## Hints

- <optional hint>

## Deployment

The flag is injected via the `FLAG` environment variable at runtime; only a placeholder lives in `deploy/flag`.

```sh
cd deploy && ../infra.sh
```

## Files

- `attachment/` — public downloadable for players (never ship the real flag here).
- `deploy/` — the live container (`Dockerfile` + entrypoint + `src/`).
- `solution/` — official exploit + writeup (organizer-only).
