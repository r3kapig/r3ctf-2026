# Tsuki's Rhythm Game

- **Author:** Aura
- **Submissions:** 97
- **Solves:** 64

## Description

Tsuki is a cryptocurrency enthusiast and the lead developer of a community rhythm game. Recently, she was testing mods and new beatmaps created by players for the game. However, a few days later, she was shocked to discover that her wallet had been completely drained.

The security response team has extracted a network traffic capture from Tsuki's work computer, along with the entire game folder of the rhythm game. Players must conduct a digital forensic analysis on these artifacts.

Players analyze the artifacts in `attachment/` and answer **11 sequential forensics questions** through a web quiz app (answers are verified against stored SHA-256 hashes). Each correct answer unlocks the next question; a special story message appears after question 9, and after all 11 questions are solved the service returns the flag. The flag is injected at runtime via the `$FLAG` environment variable (the app writes it to `/flag` on startup and reveals it after the last question); only a placeholder is committed.

Attachment download mirrors:

- [Google Drive](https://drive.google.com/file/d/1nMz5sHWJ8VENcZsBnRtw-gGRZTum83mp)
- [Baidu Pan](https://pan.baidu.com/s/1wNkbFDpRs2mHcvc89b_17A?pwd=R326)

## Files

- `attachment/attachment.7z` — player handout: `Evidence.zip`, `Game.zip`, and `traffic.pcapng` (7z-compressed, ~80 MB, also hosted on the mirrors above).
- `deploy/` — the quiz web app (Flask 3.0 on Python 3.11): `app.py`, `questions_data.json` (questions + SHA-256 hashed answers), `templates/`, `static/`, `Dockerfile`, `requirements.txt`.
- `infra.sh` — build + run script; run from inside `deploy/`.

## Deployment

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/tsukisrhythmgame:latest`
- **Port:** `5000` (Flask)
- **Flag:** dynamic — `$FLAG` env injected at runtime (infra.sh passes a placeholder `R3CTF{infra_test_flag}`); the app writes it to `/flag` and returns it after question 11.
- **Resources:** `--cpus 0.1 --memory 128m` (per infra.sh).
