# whisper

- **Category:** Pwn
- **Author:** 
- **Points:** 
- **Solves:** 

## Description

A 0-click Android exploit chain delivered through a messaging app. Craft a malicious
`.rcard` attachment, send it to a victim over the `whisper` messenger, and trigger a
heap-to-root exploit in the privileged native `whisperd` daemon inside
`com.whisper.app` to read the root-only `/flag.txt`.

## Architecture

- `attachment/whisper-local-stack.7z` — the player handout: a local reproduction of
  the FastAPI messenger backend plus a single victim runner that boots a pre-baked
  Android image. Extract it and run `./run.sh` inside to develop the exploit locally.
- `deploy/` — production infrastructure: the judge, the per-team victim pool, the
  AOSP image-baking tooling (`aosp/`), the `whisperd` binary, and the compose stack
  (nginx + backend + judge + N victim runners) under `deploy/deploy/`.

## Deployment

The real flag is injected at victim-boot time via `WHISPER_REAL_FLAG` and baked into
a root-only `/flag.txt` inside each Android image; per-team dynamic flags are derived
by the judge. Only placeholders are committed.

- Local repro (players): extract `attachment/whisper-local-stack.7z`, then
  `cd whisper-local-stack && ./run.sh`.
- Production stack (organizers): `cd deploy/deploy && ./run.sh`.

## Files

- `attachment/whisper-local-stack.7z` — player handout (local repro), 7z-compressed.
- `deploy/` — production infra (organizer-only).
