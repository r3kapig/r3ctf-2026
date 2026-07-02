---
name: creating-ctf-docker-challenges
description: Use when building a Docker container for a CTF competition challenge that serves a network service and injects a dynamic flag via the $FLAG env var at deploy time. Covers Web/Pwn/Crypto/Misc/Blockchain/Forensics challenges, xinetd/socat/nsjail forwarding, chroot/jail sandboxes, flag-scrubbing, and the ctf-docker-template scaffold.
---

# Creating CTF Docker Challenges

## Overview

A competition challenge container = **app + dynamic-flag injection + network service + sandbox**. This skill gives the decision tree, the universal skeleton, the flag-injection rules, and per-category recipes needed to build one that deploys cleanly with a single `FLAG` environment variable.

It is distilled from two sources in this reference folder:
- `ctf-docker-template/` — the CTF-Archives scaffold (the `config/` + `service/docker-entrypoint.sh` + `src/` + `docker/docker-compose.yml` convention and its flag-injection block).
- `r3ctf-2025/` — 40 real competition builds showing how the scaffold is actually adapted, and the mistakes that recur.

## When to use

- Building any remotely-deployed CTF challenge whose flag must be injected by the platform at `docker run`/`docker-compose` time.
- Choosing between xinetd/socat/direct-server/nsjail, between file/DB/argv/runtime flag delivery, and between chroot/jail/dedicated-user sandboxing.

**Not for:** pure static attachments with no service (some Reverse/Forensics), or challenges that are only a downloadable file with no remote instance.

## 1. Pick the pattern first

| Challenge type | Base image | Service front-end | Flag delivery | Sandbox | Copy from |
|---|---|---|---|---|---|
| Pwn (binary) | `ubuntu:<glibc-ver>` | **xinetd + chroot** (or `socat su=`) | `/flag` file, world- or group-readable | chroot `--userspec`, or dedicated user + rlimits | `ctf-docker-template/pwn-ubuntu_*` |
| Crypto py (no socket) | `python:3.10-slim` | **socat EXEC** | env `FLAG`, read at runtime | dedicated `ctf` user | `ctf-docker-template/crypto-python_*-no_socket` |
| Crypto py (self-listen) | `python:3.10-slim` | script's own `socket` | env `FLAG`, read at runtime | dedicated `ctf` user | `ctf-docker-template/crypto-python_*-with_socket` |
| Crypto sagemath | `sagemath/sagemath:9.6` | **socat EXEC** `sage` | env `FLAG`, read at runtime | `sage` user | `ctf-docker-template/crypto-sagemath_9.6` |
| Web PHP | `php:*-fpm-alpine` / `php:*-apache` | nginx/apache + php-fpm | `/flag` file **or** DB row | `www-data`, optional `disable_functions` | `ctf-docker-template/web-nginx-php*` / `web-lnmp-*` |
| Web Python/Node/Go/Java | matching lang image | framework / `java -jar` | `/flag` file or runtime env | dedicated user, distroless for Go | `ctf-docker-template/web-flask-*` / `web-node` / `web-java-*` |
| Misc pyjail | `python:3.10-slim` | **xinetd** or **socat** EXEC | `/flag` world-readable | pyjail + optional chroot/nsjail | `ctf-docker-template/misc-pyjail-*` |
| Misc quiz / TCP game | `python:3-alpine` | `socketserver` / custom | env `FLAG`, printed on solve | none beyond container | `r3ctf-2025/Forensics/*` |
| Blockchain EVM | `python:3.11-slim` + foundry | FastAPI proxy → local anvil | env `FLAG`, **gated reveal** over HTTP | one container per player | `r3ctf-2025/Blackchain/{miniagent,signin}` |
| Blockchain Solana | `ubuntu:22.04` + vendored validator | validator directly | `/home/ctf/flag` file | chroot-style tree | `r3ctf-2025/Blackchain/socpcl*` |

**Choose the flag-delivery model by the intended exploit** (see §3). **Choose the front-end by who owns the listening socket:** the binary/script itself → direct/`with_socket`; a dumb forwarder that spawns the app per connection → xinetd/socat `EXEC`.

## 2. The challenge package

A complete r3ctf-style challenge is more than a container — it ships the container **plus** the metadata, public downloadable, and deploy hook the platform expects. Lay it out like this:

```
<challenge>/                      # r3ctf-2026: flat (no category folder). 2025 used <category>/<challenge>/
├── README.md                   # CTFd-style metadata (Description / Author / ...) — templates/README.md
├── infra.sh                    # 2-line registry build+run, run FROM INSIDE deploy/ — templates/infra.sh
├── attachment/                 # public downloadable (binary+libc / source / .zip) — optional, see §6
├── solution/                   # solve.py + writeup.md — optional but recommended
└── deploy/                     # the live container (the infra.sh build context)
    ├── Dockerfile
    ├── service/docker-entrypoint.sh   # flag inject + start service (THE runtime entrypoint)
    ├── config/                        # xinetd / nginx / apache configs (if used)
    ├── src/                           # the author's challenge code/binary
    ├── docker/docker-compose.yml      # one-shot local test (build: ../)
    └── flag                           # placeholder ONLY (e.g. flag{test}); real flag via $FLAG
```

Role of each piece:

| Piece | Required? | Purpose |
|---|---|---|
| `deploy/Dockerfile` + entrypoint | yes | the live service players attack; reads `$FLAG` at runtime |
| `infra.sh` | yes (r3ctf convention) | reproducible registry build/run; the platform's deploy hook |
| `README.md` | recommended | title, description, author, category, points, hints |
| `attachment/` | if players need a file | the public download (never ship the real flag here) |
| `deploy/flag` placeholder | recommended | lets the image build/run locally without `-e`; overwritten at deploy |
| `solution/` | recommended | official exploit + writeup so the package is reusable/verifiable |

Conventions inherited from r3ctf-2025:
- **Dynamic flag**: injected via `$FLAG` at runtime; only a **placeholder** lives in `deploy/` and the image. The platform sets `$FLAG` per team.
- **Static flag** (Reverse / Forensics / some Crypto): ships with the attachment (and may be noted in the README) — these are fine to commit since they are the challenge answer itself.
- `infra.sh` is `docker build . -t <registry>/<chal>:latest` + `docker run --rm -d -e FLAG=... --cpus --memory -p ...`, run with `deploy/` (or the package root, if the Dockerfile needs the wider context) as the working dir.
- Entrypoint name varies in the wild (`start.sh` / `entrypoint.sh` / `service/docker-entrypoint.sh`); pick one and keep the Dockerfile in sync.
- Source lives in `deploy/src/` (or, for "repo-is-the-challenge" web/misc, at the package root).

**Dockerfile shape** (compose the pieces your category needs):
```dockerfile
FROM <base>
# 1. optional: swap apt/apk/pip mirror to ustc/tuna (China builds only — see gotcha)
# 2. install packages (xinetd / socat / nginx / lib32z1 / pip deps)
# 3. RUN useradd -m ctf            # dedicated low-priv user (uid 1000)
# 4. COPY config/...  COPY src/...  COPY service/docker-entrypoint.sh /
# 5. permissions: chown/chmod the app and the future flag location
# 6. EXPOSE <port>
# 7. ENTRYPOINT ["/docker-entrypoint.sh"]   # or CMD
```

**Entrypoint shape** (always: resolve flag → deliver it → scrub env → start service):
```sh
#!/bin/sh
# resolve + scrub (see §3 / reference/flag-injection.md)
# ... write flag to file / DB / argv ...
# ... unset FLAG ...
# start service (xinetd / socat / flask / nginx / java)
```

## 3. Flag injection — the part everyone gets wrong

Full code for every pattern: `reference/flag-injection.md`. The rules:

1. **Resolve `$FLAG`, then scrub it to `no_FLAG`** so the app cannot leak it via `env` or `/proc/<pid>/environ`. Falls back to a test placeholder when `FLAG` is unset (e.g. a local run without `-e`) so the container still starts:
   ```sh
   if [ -n "$FLAG" ]; then
       INSERT_FLAG="$FLAG"
       export FLAG=no_FLAG
       FLAG=no_FLAG
   else
       INSERT_FLAG="flag{TEST_Dynamic_FLAG}"
   fi
   ```

2. **Pick delivery by intended exploit:**
   - **RCE/escape → flag file**, readable by the compromised uid (`chmod 744 /flag` or group `ctf`).
   - **Privesc/exploit → root-only file** (`chmod 400`, `/root/flag_<rand>.txt`); randomize the name to force discovery.
   - **XSS → flag held only by the bot** (file `chown bot:bot chmod 400`, or a cookie/localStorage the bot sets); scrub it from the app container.
   - **Quiz/solve-gated → keep in env, print on success** (crypto/forensics). Accept that the flag is then in the process environment — only safe if the app never exposes env/file reads.
   - **Blockchain → gated HTTP reveal**: the proxy returns `FLAG` only when `isSolved()` is true on-chain.

3. **Scrub unless the app must read it.** If the flag stays in the environment, any accidental env/file read leaks it. r3ctf-2025's crypto and forensics challenges leave `FLAG` unscrubbed by design (flag printed on solve) — this is a deliberate, exploitable-by-mistake choice; do not copy it for a challenge where env reads are in scope.

4. **Set flag-file permissions to the intended reader and no one else.** World-readable `/flag` (`744`) is only correct when the whole point is "RCE ⇒ cat /flag". For anything harder, lock it down and provide a `setuid /readflag` or bot-only path.

## 4. Service forwarding

Full configs: `reference/service-forwarding.md`. Quick pick:
- **xinetd** — pwn/pyjail, supports `server = /usr/sbin/chroot` + `--userspec=1000:1000`, plus `per_source`/`rlimit_cpu`/`rlimit_as` limits. Start with `/etc/init.d/xinetd start; sleep infinity;`.
- **socat EXEC** — crypto/pyjail/sagemath, simplest per-connection fork: `socat TCP-LISTEN:<port>,fork,reuseaddr EXEC:"<cmd>",stderr`. Add `su=<user>` or wrap `su <user> -c` to drop privileges.
- **direct / with_socket** — the app itself listens (flask/node/go/java/http.server/socketserver). Use for web, blockchain proxy, quiz servers.
- **nsjail (`pwn.red/jail`)** — code-execution sandboxes; drive with `JAIL_TIME/JAIL_MEM/JAIL_CPU/JAIL_PIDS/JAIL_CONNS_PER_IP` env. Needs `privileged: true`.

## 5. Sandboxing menu (layer what fits)

- **Dedicated user** (`useradd -m ctf`, drop via xinetd `user =` / socat `su=` / `USER`) — baseline for everything.
- **chroot** — pwn: xinetd `chroot --userspec=1000:1000 /home/ctf ./attachment` with a jail tree (copied `lib*`, `/dev/{null,zero,random,urandom}` via `mknod`, minimal `bin/{sh,ls,cat,timeout}`).
- **nsjail** — for running untrusted player code (`pwn.red/jail`).
- **PHP hardening** — `disable_functions` + `open_basedir`; run FPM as the app user; add a `setuid /readflag` so the flag stays root-only.
- **Distroless runtime** — for Go services, multi-stage build into `gcr.io/distroless/static` (no shell/pkgmgr).
- **Resource limits** — always: xinetd `per_source`/`rlimit_cpu`/`rlimit_as`, and `docker run --cpus --memory` (r3ctf uses `--cpus 0.1 --memory 128m`).

## 6. `attachment/` vs `deploy/` split

Ship a separate public artifact only when it must differ from the live service:
- **Pwn**: `attachment/` = binary + libc/ld for players; `deploy/files/` = same + the real `flag` placeholder (never ship the flag).
- **Reverse**: identical binary in both; only the embedded/env flag differs (`R3CTF{not_a_real_flag}` in attachment).
- **Web/Misc**: often a `.zip` of source as the attachment, full service in `deploy/`.

Don't split if they're identical — it only invites drift (r3ctf has attachment Dockerfiles that don't even build standalone).

## 7. Build, test, deploy

- **Local test** — `docker/docker-compose.yml`: `build: ../`, `environment: FLAG: "..."`, `ports: <host>:<container>`, `restart: unless-stopped`. `cd docker && docker-compose up -d`.
- **Production** — `infra.sh`: `docker build . -t <registry>/<chal>:latest && docker run --rm -d -e FLAG=... --cpus 0.1 --memory 128m -p <host>:<container> <registry>/<chal>:latest`.
- **Multi-service** (e.g. web app + XSS bot): one `docker-compose.yml` with both builds; keep the flag out of containers that don't need it.

## Common mistakes (all seen in real challenges)

| Symptom | Cause / fix |
|---|---|
| `/docker-entrypoint.sh: line 2: $'\r': command not found` | CRLF line endings from Windows. Fix: `sed -i 's/\r//' docker-entrypoint.sh` (GNU sed) or clone on Linux. |
| `EXPOSE 10001` but service binds `10002` | `EXPOSE` is documentary; the real mapping is platform-side. Keep them in sync and document the real port. |
| Flag leaked via `/proc/self/environ` / `getenv()` | Entrypoint didn't scrub `FLAG`. `unset FLAG` (or overwrite to `no_FLAG`) after delivering it. |
| Cleanup `rm -rf /docker-entrypoint.sh` never runs | It sits **after** `sleep infinity`. Delete it **before** starting the long-running service. |
| Build slow/failing outside China | ustc/tuna mirror lines. Remove them when building outside mainland China / behind a proxy. |
| mysql line-continuation breaks | Space after `\` in `mysqladmin ... \ `. Delete the trailing space. |
| `setuid /readflag` but `/flag` is world-readable | Pointless — lock `/flag` to root (`chmod 400`/`740`) so the setuid binary is the only path. |
| Player gets the flag in the attachment | `attachment/` and `deploy/` shipped the same flag. Use a placeholder in the attachment. |
| `service/` runit/entrypoint runs app as root | Drop to the dedicated user (`su`, `USER`, xinetd `user =`) before exec. |
| Reused template README/README mismatch | The README says chroot but the xinetd config doesn't chroot, or port mismatch in `infra.sh`. Keep README/Dockerfile/config/infra.sh consistent. |
| KOH security `rm` is a no-op | Typos `sockert.py`/`sockertserver.py`/`site-package`. Use real names `socket.py`/`socketserver.py`/`site-packages`. |
| Go service flag can't be injected by platform | Flag baked via `COPY .env` at build time. Prefer runtime `-e FLAG` unless per-team derivation is required. |
| `Unable to locate package lib32z1` on arm64 | `lib32z1` is x86-only 32-bit support. Drop it on arm64 or for a native 64-bit binary. |
| Flag file owned `root:root`, not `root:ctf` | `touch /home/ctf/flag` ran **after** `chown -R`. Create the flag before chown, or `chown root:ctf /home/ctf/flag` explicitly — matters once the flag is not world-readable. |

## Verification checklist

1. `docker build` succeeds with no mirror errors (or mirrors removed for your network).
2. `docker-compose up -d` (or `infra.sh`) starts; the port is reachable.
3. Connect as a player: the service responds; the flag is **not** visible before the intended solve.
4. After the intended solve, the flag is readable **only** by the intended path (file/bot/env/HTTP).
5. `docker run ... -e FLAG=r3ctf{real}` injects the platform flag; the test placeholder is gone.
6. **Scrub check (check the right process):** `export FLAG=no_FLAG` scrubs the environment inherited by **child processes** — so verify the **forwarder/challenge** process, not PID 1. `docker exec ... sh -c 'cat /proc/$(pgrep -f xinetd)/environ | tr "\0" "\n" | grep -i flag'` should show `FLAG=no_FLAG` (the real value gone). Do **not** rely on PID 1's `/proc/1/environ` (immutable from a shell) or `docker exec ... env` (reconstructs the original `-e` from the container spec) — both legitimately still show the real flag and are not player-reachable.
7. Resource limits (`--cpus`/`--memory` or xinetd rlimits) are set.
8. README, Dockerfile, xinetd/socat config, compose, and `infra.sh` all agree on port, flag path, and sandbox model.

## Reference files

- `reference/flag-injection.md` — every flag-delivery mechanism with copy-paste code and when to use each.
- `reference/service-forwarding.md` — xinetd (chroot), socat, nsjail, and direct-server configs.
- `reference/category-recipes.md` — full skeleton per category (pwn, crypto python/sagemath, web php/flask, misc pyjail/quiz, blockchain EVM).
- `templates/` — minimal copy-paste starters: `README.md` (challenge metadata), `infra.sh` (registry build/run), `flag-entrypoint.sh`, `ctf.xinetd`, `socat-exec.sh`, `docker-compose.yml`.
- Worked real examples throughout `r3ctf-2025/<Category>/<challenge>/deploy/` and the scaffolds in `ctf-docker-template/`.
