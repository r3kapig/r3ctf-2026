FROM ubuntu:24.04@sha256:023f8a753c22258c9fe2d0005a7d28258038da7d620e9f93e9ad78aa266f9f11 AS build

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        cmake \
        python3 \
        python3-pip \
        python3-venv \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

COPY services/proxy ./services/proxy
RUN cmake -S services/proxy -B build/proxy -DCMAKE_BUILD_TYPE=Release \
    && cmake --build build/proxy --parallel \
    && mkdir -p services/proxy/bin \
    && cp build/proxy/P1gROXY services/proxy/bin/P1gROXY

COPY services/warehousehub/requirements.txt ./services/warehousehub/requirements.txt
RUN python3 -m venv /opt/p1groxy-venv \
    && /opt/p1groxy-venv/bin/pip install --no-cache-dir -r services/warehousehub/requirements.txt

FROM ubuntu:24.04@sha256:023f8a753c22258c9fe2d0005a7d28258038da7d620e9f93e9ad78aa266f9f11

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/opt/p1groxy-venv/bin:${PATH}"
ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        bash \
        ca-certificates \
        libstdc++6 \
        python3 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -r -u 10001 -d /nonexistent -s /usr/sbin/nologin warehousehub

WORKDIR /opt/p1groxy

COPY --from=build /build/services/proxy/bin ./services/proxy/bin
COPY --from=build /opt/p1groxy-venv /opt/p1groxy-venv
COPY services/warehousehub ./services/warehousehub
COPY deploy ./deploy

RUN chmod +x deploy/run-container.sh \
    && printf '%s\n' 'r3ctf{FLAG}' > /flag.txt \
    && chown root:root /flag.txt \
    && chmod 0444 /flag.txt

USER warehousehub
EXPOSE 8080
CMD ["./deploy/run-container.sh"]
