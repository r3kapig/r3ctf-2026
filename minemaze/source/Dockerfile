# syntax=docker/dockerfile:1

FROM eclipse-temurin:25-jre-noble

ENV INIT_MEMORY=1G \
    MAX_MEMORY=4G \
    JAVA_OPTS=""

WORKDIR /server

# `assets/server` is a prebuilt server root containing Folia, libraries, versions,
# cache, configs, GrimAC, RekaMaze, and the Rekamaze datapack. It intentionally
# excludes old world region data.
COPY assets/server/ ./

RUN echo "eula=true" > eula.txt \
    && sed -i 's/^initial-enabled-packs=.*/initial-enabled-packs=vanilla,file\/rekamaze/' server.properties \
    && sed -i 's/^max-players=.*/max-players=2/' server.properties \
    && sed -i 's/^online-mode=.*/online-mode=false/' server.properties

EXPOSE 25565

CMD ["sh", "-c", "rm -rf world/dimensions/rekamaze world_rekamaze_maze world/rekamaze && exec java $JAVA_OPTS -Xms$INIT_MEMORY -Xmx$MAX_MEMORY -jar folia-26.1.2-8.jar nogui"]
