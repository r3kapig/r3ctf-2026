# r3reach

- **Category:** Misc
- **Author:** Wings
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

A Minecraft (Paper) server challenge. Join the server and capture the flag
without getting close — the `R3Reach` plugin gates the flag behind a reach check
("Capture the flag without getting close"). Find a way to reach the flag
villager from farther than intended.

Plugin commands: `/magic` ("Something magical happens..."), `/reset`
("Reset the challenge").

## Files

- `attachment/R3Reach-1.0.jar` — player handout (the challenge plugin, for
  local analysis).
- `deploy/` — the live Paper server: `Dockerfile`, `start.sh`,
  `server.properties`, `plugins/R3Reach-1.0.jar`, `plugins/R3Reach/config.yml`.

## Deployment

Paper 26.2 server (Java 25), listening on TCP **25565**. The plugin reads the
flag from `plugins/R3Reach/config.yml` (`flag:`).

**Dynamic flag**: the platform injects `$FLAG`; `start.sh` rewrites the first
line of `plugins/R3Reach/config.yml` to `flag: $FLAG` and scrubs the env before
launching the server.

```sh
cd deploy && ../infra.sh
```

- **Image:** `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3reach:latest`
- **Port:** container `25565` (Minecraft), host `25565`
- **Flag env:** `FLAG`
- **Notes:** the server JVM runs with `-Xms1G -Xmx2G`; give the container ~3 GB
  RAM. The matching vanilla server jar + generated world are **baked into the
  image at build time** (the Dockerfile starts the server once, waits for
  `Done`, then shuts it down), so the runtime starts in ~15 s and needs **no
  egress** — it even reaches `Done` under `--network none`. Paper still makes
  two non-blocking background calls at startup (an update check to
  `fill.papermc.io` and a metrics/session call); if egress is available they
  succeed silently, if not they fail harmlessly and never block startup.
  `max-players=1`, adventure mode, peaceful void world.
