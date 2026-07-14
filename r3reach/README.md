# r3reach

- **Author:** Wings
- **Submissions:** 38
- **Solves:** 11

## Description

We all know the classic Minecraft "Reach" hack. For this challenge, we've
locked down the server and disabled any form of Reach modifications. Your
objective is to interact with the Flag from a distance that should be
impossible. Can you outsmart the restrictions and reach the flag?

The live service is a Paper Minecraft server running the `R3Reach` plugin on a
single-slot, adventure-mode, peaceful void world. The plugin reads the flag
from `plugins/R3Reach/config.yml` (`flag:`); players get it by triggering the
flag interaction from beyond the enforced reach limit. Plugin commands:
`/magic` ("Something magical happens...") and `/reset` ("Reset the challenge").

## Files

- `attachment/R3Reach-1.0.jar` — player handout (the challenge plugin, for
  local analysis).
- `deploy/` — the live Paper server: `Dockerfile`, `docker-compose.yml`,
  `start.sh`, `server.properties`, `plugins/R3Reach-1.0.jar`,
  `plugins/R3Reach/config.yml`.
- `infra.sh` — build + run script (run from inside `deploy/`).

## Deployment

Paper 26.2 server (Java 25), listening on TCP **25565**.

**Dynamic flag**: the platform injects `$FLAG`; `start.sh` rewrites the first
line of `plugins/R3Reach/config.yml` to `flag: $FLAG` and scrubs the env
before launching the server.

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3reach:latest`
- **Port:** container `25565` (Minecraft), host `25565`
- **Flag env:** `FLAG`
- **Notes:** the server JVM runs with `-Xms1G -Xmx2G`; give the container ~3 GB
  RAM (infra.sh: `--cpus 2.0 --memory 3g`). The matching vanilla server jar +
  generated world are **baked into the image at build time** (the Dockerfile
  starts the server once, waits for `Done`, then shuts it down), so the runtime
  starts in ~15 s and needs **no egress** — it even reaches `Done` under
  `--network none`. Paper still makes two non-blocking background calls at
  startup (an update check to `fill.papermc.io` and a metrics/session call); if
  egress is available they succeed silently, if not they fail harmlessly and
  never block startup. `max-players=1`, adventure mode, peaceful void world.
