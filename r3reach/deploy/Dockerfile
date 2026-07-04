FROM eclipse-temurin:25-jre AS builder

WORKDIR /server

ADD https://fill-data.papermc.io/v1/objects/4e1ab8b87f780d6d7e367115312d3798aef35f77e4634529d88abfa84683244b/paper-26.2-40.jar .
RUN echo "eula=true" > eula.txt
COPY server.properties .
COPY plugins/ plugins/
COPY start.sh .

RUN chmod +x start.sh && test -s paper-26.2-40.jar

FROM eclipse-temurin:25-jre

RUN adduser --disabled-password --gecos "" paper \
  && mkdir -p /home/paper/server \
  && chown -R paper:paper /home/paper
USER paper

WORKDIR /home/paper/server
COPY --from=builder --chown=paper:paper /server /home/paper/server

EXPOSE 25565
CMD ["./start.sh"]
