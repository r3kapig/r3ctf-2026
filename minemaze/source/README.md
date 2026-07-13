# minemaze source (rekamaze-folia build context)

This is the **build context** the author used to produce the `rekamaze-folia`
image (which we retag as `minemaze:latest`). It is kept here for reference only —
the image is **already built**, so nothing here needs building.

## What's here

```text
Dockerfile                       # eclipse-temurin:25-jre-noble + COPY assets/server
docker-compose.yml               # author's compose (rekamaze-folia:latest)
assets/server/
├── config/                      # Paper global + world-defaults configs
├── plugins/
│   ├── RekaMaze-1.0.0.jar       # the challenge plugin (blind maze / lock-and-key)
│   └── RekaMaze/config.yml      # maze size, doors, bubble radius, time limit
├── world/datapacks/rekamaze/    # the `rekamaze` dimension datapack (maze.json)
└── *.yml / *.json / *.properties
                                 # server.properties, bukkit/spigot/paper configs
```

The challenge logic lives in the `RekaMaze` plugin; the awarded flag is read from
the `FLAG` environment variable (see `assets/server/plugins/RekaMaze/config.yml`).

## What's deliberately excluded (see `.gitignore`)

These large **third-party** files ship inside the published image but are not
challenge source, so they're kept out of git (the original `src.tar` was ~223 MB,
mostly these):

| Path | Size | What it is |
|---|---|---|
| `assets/server/folia-26.1.2-8.jar` | ~51 MB | Folia server jar |
| `assets/server/libraries/` | ~72 MB | Folia/Mojang dependency jars |
| `assets/server/cache/` | ~58 MB | Mojang server cache (`mojang_26.1.2.jar`) |
| `assets/server/versions/` | ~28 MB | Folia version jars |
| `assets/server/plugins/grimac-bukkit-*.jar` | ~12 MB | GrimAC anti-cheat plugin |
| `assets/server/plugins/GrimAC/` | ~2.5 MB | GrimAC configuration |

To recreate a full buildable context, drop those files back into the same paths
(the author’s original `src.tar` has them) and run `docker build`.
