# MineMaze

- **Category:** Misc (Minecraft)
- **Author:**
- **Difficulty:**
- **Wave:**
- **Points:**
- **Solves:**

## Description

Players must connect to the challenge server and complete a procedurally generated maze within the time limit. The maze
is hidden by limited visibility, protected by locked doors, and requires collecting keys in the correct order before reaching the exit.

### Client Requirements

Please use the following client environment:

- Minecraft `26.1.2`
- Fabric Loader `0.19.3`
- Fabric API `0.153.0+26.1.2` or later
- Install the provided client mod: `gmtoolbox-1.0.0.jar`

The GM Toolbox mod is required for the intended challenge experience. Make sure it is placed in your Minecraft `mods` folder together with Fabric API before joining the server.

## How to play

1. Set up the client environment from "Client Requirements" above (Fabric
   Loader + Fabric API + `gmtoolbox-1.0.0.jar`) and connect to the server (the
   server runs `online-mode=false`, so no Mojang/Microsoft account is
   required).
2. Run `/startgame` to begin a maze run.
3. Explore the maze, collect keys, open the locked doors, and reach the goal.
4. On completion the server tells you the flag.

Other commands: `/leavegame` (abandon your run). Admins: `/rekamaze info`,
`/rekamaze stop <player>`, `/rekamaze reload`.

Per-run limits (from `plugins/RekaMaze/config.yml`): 1 hour time limit, 10s
start cooldown, `max-players=2` per instance.

## Files

- `attachment/gmtoolbox-1.0.0.jar` — player handout: the GM Toolbox client mod
  (install into your Minecraft `mods` folder alongside Fabric API).
- `attachment/player_rules.pdf` — player handout: challenge rules / how-to-play.
- `deploy/docker-compose.yml` — runs the `minemaze` image (Folia 26.1.2,
  RekaMaze + GrimAC plugins). Exposes `25565`.
- `infra.sh` — pull + run a local test instance on `:25565`.
- `source/` — the author's `rekamaze-folia` build context (Dockerfile, server
  configs, RekaMaze plugin jar, maze datapack). Reference only — the image is
  already built; large third-party server binaries are excluded (see
  `source/README.md`).

The server jar, plugins, world datapack and configs are all baked into the
image; the player-side attachment is the GM Toolbox client mod plus the rules
PDF above.

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
