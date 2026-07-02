ARG BASE_PLATFORM=linux/amd64
ARG UBUNTU_2404_AMD64=ubuntu:24.04@sha256:52df9b1ee71626e0088f7d400d5c6b5f7bb916f8f0c82b474289a4ece6cf3faf
FROM --platform=${BASE_PLATFORM} ${UBUNTU_2404_AMD64}

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        socat \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -r -u 10001 -g nogroup -d /nonexistent -s /usr/sbin/nologin ctf

COPY attachment/ploys /app/ploys
COPY deploy/start.sh /app/start.sh

RUN chmod 0555 /app/ploys /app/start.sh

EXPOSE 1337

CMD ["/app/start.sh"]
