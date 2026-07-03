FROM debian:bookworm-slim AS builder

# 制作者信息
LABEL auther_template="CTF-Archives"

# apt更换镜像源，并更新软件包列表信息
RUN set -eux; \
    for file in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources; do \
        [ -f "$file" ] || continue; \
        sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g; s/security.debian.org/mirrors.ustc.edu.cn/g' "$file"; \
    done
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    cmake \
    libboost-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY ./src/ /build/

RUN cmake -S . -B build -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_SHARED_LIBS=OFF \
        -DSEAL_BUILD_DEPS=OFF \
        -DSEAL_USE_MSGSL=OFF \
        -DSEAL_USE_ZLIB=OFF \
        -DSEAL_USE_ZSTD=OFF \
        -DSEAL_USE_INTEL_HEXL=OFF \
        -DSEAL_BUILD_EXAMPLES=OFF \
        -DSEAL_BUILD_TESTS=OFF \
        -DSEAL_BUILD_BENCH=OFF \
        -DSEAL_BUILD_SEAL_C=OFF \
    && cmake --build build -j --target he_server

FROM debian:bookworm-slim

LABEL auther_template="CTF-Archives"

RUN set -eux; \
    for file in /etc/apt/sources.list /etc/apt/sources.list.d/*.sources; do \
        [ -f "$file" ] || continue; \
        sed -i 's/deb.debian.org/mirrors.ustc.edu.cn/g; s/security.debian.org/mirrors.ustc.edu.cn/g' "$file"; \
    done
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libstdc++6 \
        socat \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY --from=builder /build/build/he_server /app/he_server
COPY ./service/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/he_server /app/docker-entrypoint.sh

# 新建用户，并进行账户改变
RUN useradd -m ctf
RUN chown -R ctf:ctf /app
USER ctf

EXPOSE 9999

# 指定容器入口点
ENTRYPOINT ["/app/docker-entrypoint.sh"]
