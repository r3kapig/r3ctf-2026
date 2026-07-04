# minemaze

- **Category:** Misc (Minecraft)
- **Author:**
- **Difficulty:**
- **Wave:**
- **Points:**
- **Solves:**

## Description

**MineMaze** — a blind, fog-of-war maze on a Folia server. Each run generates a
200×200 cell maze with 8 locked doors and matching keys; you only see a small
"bubble" of blocks around you, so you have to explore, collect keys, and unlock
doors by memory. Reach the goal before the timer runs out and the server awards
you the flag.

## How to play

1. Connect to the server with a **vanilla Minecraft 1.21.x** client (the server
   runs `online-mode=false`, so no Mojang/Microsoft account is required).
2. Run `/startgame` to begin a maze run.
3. Explore the maze, collect keys, open the locked doors, and reach the goal.
4. On completion the server tells you the flag.

Other commands: `/leavegame` (abandon your run). Admins: `/rekamaze info`,
`/rekamaze stop <player>`, `/rekamaze reload`.

Per-run limits (from `plugins/RekaMaze/config.yml`): 1 hour time limit, 10s
start cooldown, `max-players=2` per instance.

## Files

- `deploy/docker-compose.yml` — runs the `minemaze` image (Folia 26.1.2,
  RekaMaze + GrimAC plugins). Exposes `25565`.
- `infra.sh` — pull + run a local test instance on `:25565`.
- `source/` — the author's `rekamaze-folia` build context (Dockerfile, server
  configs, RekaMaze plugin jar, maze datapack). Reference only — the image is
  already built; large third-party server binaries are excluded (see
  `source/README.md`).

The server jar, plugins, world datapack and configs are all baked into the
image; there is no player-side attachment (just connect with a vanilla client).

## Dynamic flag

Each instance is per-team: the platform injects the team's flag via the `FLAG`
environment variable. The `RekaMaze` plugin reads `FLAG` at runtime and awards
it to the player when they complete the maze. If `FLAG` is unset the plugin
falls back to the placeholder `r3ctf{FLAG_NOT_CONFIGURED}` — so a real `FLAG`
must always be provided.

Image: `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/minemaze:latest`
(retagged from the author's `rekamaze-folia:latest`).

## Resources

- CPU: ~2 cores
- Memory: ~4g (JVM `-Xms1G -Xmx3G` + overhead)
- Port: `25565` (Minecraft)
