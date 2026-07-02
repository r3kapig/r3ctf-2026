FROM ubuntu:26.04

RUN apt-get update && \
    apt-get install -y --no-install-recommends openssl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY ./fw_ctf_host              /app/fw_ctf_host
COPY ./lib                         /opt/lib
COPY ./entrypoint.sh /entrypoint.sh

RUN chmod +x /app/fw_ctf_host /entrypoint.sh /opt/lib/ld-linux-x86-64.so.2 && \
    ln -sf libz.so.1.3.1    /opt/lib/libz.so.1 && \
    ln -sf libzstd.so.1.5.7 /opt/lib/libzstd.so.1

RUN mkdir -p /app/certs && \
    openssl req -x509 -newkey rsa:2048 -nodes \
        -keyout /app/certs/server.key \
        -out /app/certs/server.crt \
        -days 3650 -subj "/CN=eazyvpn.local" >/dev/null 2>&1 && \
    chmod 600 /app/certs/server.key

RUN touch /app/flag && chmod 444 /app/flag

EXPOSE 4433

ENTRYPOINT ["/bin/sh", "/entrypoint.sh"]
