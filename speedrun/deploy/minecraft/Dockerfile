FROM itzg/minecraft-server:java21

ENV EULA=TRUE \
    TYPE=PAPER \
    VERSION=1.21.10 \
    MEMORY=2G \
    ONLINE_MODE=FALSE \
    SPEEDRUN_RUN_TIMEOUT_SECONDS=3600 \
    ENABLE_RCON=true \
    SPEEDRUN_CODES_FILE=/shared/codes.json \
    RESET_WORLD_ON_START=true \
    RANDOMIZE_SEED_ON_START=true

RUN mkdir -p /data/plugins /shared

COPY --chown=1000:1000 minecraft/plugins/ /data/plugins/
COPY --chown=1000:1000 minecraft/bukkit.yml /data/bukkit.yml
COPY --chown=1000:1000 minecraft/start-with-random-seed.sh /start-with-random-seed.sh
COPY --chown=1000:1000 shared/codes.json /shared/codes.json

RUN chmod +x /start-with-random-seed.sh \
    && chown -R 1000:1000 /data/plugins /data/bukkit.yml /shared

EXPOSE 25565

ENTRYPOINT ["/bin/bash", "/start-with-random-seed.sh"]
