FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
 && rm -rf /var/lib/apt/lists/*
COPY chatserver-1.0.0-linux-amd64 /usr/local/bin/chatserver
COPY certs/ca.crt certs/server.crt certs/server.key /certs/
RUN mkdir -p /data/avatars
EXPOSE 8443
CMD ["chatserver", "-addr", ":8443", "-certs", "/certs", "-db", "/data/r3chat.db", "-avatars", "/data/avatars"]
