# definitely-not-a-web-chal

- **Category:** Pwn
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

It's served over HTTP, but it is *definitely* not a web challenge.

A patched PHP interpreter (a pinned `php-src` commit with `heap-isolation` and
`metadata-ro` patches) runs behind nginx + php-fpm. The flag lives at `/flag`
(root-only `0400`) and is only readable through the setuid-root `/readflag`
helper. Pop the interpreter, escalate, and exec `/readflag`.

## Files

- `attachment/to-player.zip` — player handout: the build context
  (`Dockerfile`, nginx `default`, `index.php`, `php.ini`, patches,
  `readflag.c`, `init.sh`, `Readme.md`) so players can reproduce the
  environment locally with their own `FLAG` environment variable.
- `deploy/` — the live container (same sources as the handout).
- `solve.py` — reference solver.

## Deployment

Builds PHP from source (a pinned `php-src` commit + two patches), so the image
build is CPU-heavy (~10–20 min).

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/definitely-not-a-web-chal:latest`
- **Port:** container `80` (nginx), exposed as host `8082` in `infra.sh`
- **Flag:** passed through `FLAG`, written to `/flag` at startup, scrubbed from
  the runtime environment, and read via setuid `/readflag`
