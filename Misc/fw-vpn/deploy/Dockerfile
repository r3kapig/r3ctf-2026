FROM ubuntu:26.04

RUN apt-get update && apt-get install -y --no-install-recommends \
        libssl3t64 ca-certificates openssl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY src/fw_ctf_host ./fw_ctf_host
COPY service/docker-entrypoint.sh /entrypoint.sh
COPY flag ./flag
RUN mkdir -p certs && \
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout certs/server.key \
        -out certs/server.crt \
        -days 3650 \
        -subj "/CN=eazyvpn.local" >/dev/null 2>&1 && \
    chmod 600 certs/server.key && \
    chmod +x ./fw_ctf_host /entrypoint.sh

EXPOSE 4433

ENTRYPOINT ["/entrypoint.sh"]
CMD ["./fw_ctf_host"]
