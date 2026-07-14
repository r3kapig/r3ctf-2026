# definitely-not-a-web-chal

- **Author:** Frank & Xia0
- **Submissions:** 34
- **Solves:** 10

## Description

Remote OBO Nday in PHP, it is already well documented, so nothing could go wrong, right?

Despite the web façade (nginx + PHP-FPM serving a single `index.php`), this is a
pwn challenge. PHP is built from a pinned `php-src` commit with two custom
hardening patches applied — heap isolation and read-only heap metadata — so the
"well documented" bug is no longer trivial to exploit. The attack surface is the
`md5_file($_POST['file'])` call with a fully player-controlled `file` argument,
which enables `php://filter/convert.iconv.UTF-8.ISO-2022-CN-EXT/...` filter
tricks to trigger an out-of-bounds write in the iconv conversion path (the
Dockerfile deliberately restores the `ISO-2022-CN-EXT.so` gconv module).
Intended solve (see `solve.py`): heap fengshui to shape the Zend allocator,
leak heap/libc addresses, obtain an arbitrary write, hijack control flow to
call `system("/readflag>1.php")`, then fetch the result over HTTP. The flag
itself lives at `/flag` (root, mode `0400`) and is only readable through the
setuid `/readflag` binary.

## Files

- `attachment/to-player.zip` — player handout: the build context
  (`Dockerfile`, nginx `default`, `index.php`, `php.ini`, patches,
  `readflag.c`, `init.sh`, `Readme.md`) so players can reproduce the
  environment locally with their own `FLAG` environment variable.
- `deploy/` — the live container (same sources as the handout):
  `Dockerfile` builds PHP from source (pinned commit + `heap-isolation.patch`
  and `metadata-ro.patch`), `init.sh` is the entrypoint, `readflag.c` is the
  setuid flag reader, `default`/`index.php`/`php.ini` are the web stack.
- `infra.sh` — build + run script (run from inside `deploy/`).
- `solve.py` — reference solver (heap fengshui → leak → arbitrary write → RCE →
  `/readflag`).

## Deployment

Builds PHP from source (a pinned `php-src` commit + two patches), so the image
build is CPU-heavy (~10–20 min).

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/definitely-not-a-web-chal:latest`
- **Port:** container `80` (nginx → PHP-FPM on `127.0.0.1:9000`), exposed as
  host `8082` in `infra.sh`
- **Resources:** 0.5 CPU, 256 MB memory
- **Flag:** dynamic — `FLAG` env is written to `/flag` (root, `0400`) at
  startup by `init.sh`, then scrubbed from the environment (`unset FLAG`);
  the flag is only readable via the setuid `/readflag` binary
