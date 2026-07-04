FROM eclipse-temurin:25-jre AS builder

WORKDIR /server

ADD https://fill-data.papermc.io/v1/objects/4e1ab8b87f780d6d7e367115312d3798aef35f77e4634529d88abfa84683244b/paper-26.2-40.jar .
RUN echo "eula=true" > eula.txt
COPY server.properties .
COPY plugins/ plugins/
COPY start.sh .

RUN chmod +x start.sh && test -s paper-26.2-40.jar

# Bake the vanilla server jar + generated world into the image so the runtime
# needs no egress. Start the server once, wait for "Done", then shut it down.
RUN { \
      java -Xms1G -Xmx2G -jar paper-26.2-40.jar nogui > /tmp/srv.log 2>&1 & \
      SRV=$!; \
      ok=0; \
      for i in $(seq 1 180); do \
        if grep -q "Done (" /tmp/srv.log 2>/dev/null; then ok=1; break; fi; \
        if ! kill -0 $SRV 2>/dev/null; then break; fi; \
        sleep 2; \
      done; \
      echo "=== bake: server log tail ==="; tail -20 /tmp/srv.log; \
      if [ "$ok" != "1" ]; then echo "SERVER DID NOT REACH DONE"; exit 1; fi; \
      kill $SRV 2>/dev/null; sleep 8; kill -9 $SRV 2>/dev/null || true; wait $SRV 2>/dev/null || true; \
      echo "=== bake complete, server dir ==="; ls -la /server; \
    }

FROM eclipse-temurin:25-jre

RUN adduser --disabled-password --gecos "" paper \
  && mkdir -p /home/paper/server \
  && chown -R paper:paper /home/paper
USER paper

WORKDIR /home/paper/server
COPY --from=builder --chown=paper:paper /server /home/paper/server

EXPOSE 25565
CMD ["./start.sh"]
