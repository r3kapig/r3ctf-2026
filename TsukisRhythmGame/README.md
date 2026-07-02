# Tsuki's Rhythm Game

- **Category:** Misc / Forensics
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

Tsuki is a cryptocurrency enthusiast and the lead developer of a community rhythm
game. Recently, she was testing mods and new beatmaps created by players for the
game. However, a few days later, she was shocked to discover that her wallet had
been completely drained.

Currently, the security response team has extracted a network traffic capture
from Tsuki's work computer, along with the entire game folder of the rhythm game.
Please conduct a digital forensic analysis on them.

## How it works

Players analyze the artifacts in `attachment/` and answer **11 sequential
forensics questions** through the web app (an MD5/answer-checker). Each correct
answer unlocks the next; after all 11 are solved the service returns the flag.

The flag is injected at runtime via `$FLAG` (the app writes it to `/flag` on
start and reveals it after the last question). Only a placeholder is committed.

## Files

- `attachment/attachment.7z` — player handout: `Evidence.zip`, `Game.zip`, and
  `traffic.pcapng` (7z-compressed, ~80 MB).
- `deploy/` — the quiz web app (Flask): `app.py`, `questions_data.json`,
  `templates/`, `static/`.

## Deployment

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/tsukisrhythmgame:latest`
- **Port:** `5000` (Flask)
- **Flag env:** `FLAG` (also surfaced to solvers after Q11)
