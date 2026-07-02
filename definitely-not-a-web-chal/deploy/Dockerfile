FROM ubuntu@sha256:6d7b5d3317a71adb5e175640150e44b8b9a9401a7dd394f44840626aff9fa94d
# Ubuntu 22.04 LTS (Jammy Jellyfish) image as of 2024-04-16
# https://hub.docker.com/layers/library/ubuntu/jammy-20240416/images/sha256-e8ac95e1b49f06d0533601ed1eb609d9b553f38cfe39f295868604ea83ee4d6d

# `apt-mark hold libc6` won't work
RUN cp /usr/lib/x86_64-linux-gnu/gconv/ISO-2022-CN-EXT.so /tmp/iso.back  
RUN apt-get update && apt-get install -y build-essential autoconf automake bison flex re2c gdb python2 \
            curl file binutils libtool make pkgconf valgrind git libxml2-dev libsqlite3-dev nginx \
            ca-certificates libbz2-dev libz-dev libcurl4-openssl-dev libonig-dev libssl-dev libreadline-dev \
            libedit-dev libfcgi-dev --no-install-recommends

RUN cp /tmp/iso.back /usr/lib/x86_64-linux-gnu/gconv/ISO-2022-CN-EXT.so

WORKDIR /app

ARG PHP_SRC_REPO=https://github.com/php/php-src.git
ARG PHP_SRC_COMMIT=25360ef24951f1c6b83f8bf85fbdcaff4a1a40e1
RUN git init php-src && \
    cd php-src && \
    git remote add origin "$PHP_SRC_REPO" && \
    git fetch --depth 1 origin "$PHP_SRC_COMMIT" && \
    git checkout --detach FETCH_HEAD

COPY ["php.ini", "/tmp"]
COPY heap-isolation.patch /heap-isolation.patch
COPY metadata-ro.patch /metadata-ro.patch
COPY ["default", "/etc/nginx/sites-available/"]

RUN cd php-src && \
    git apply --whitespace=fix /heap-isolation.patch && \
    git apply --whitespace=fix /metadata-ro.patch && \
    ./buildconf --force && \
    ./configure --with-bz2 --with-zlib --with-iconv --enable-mbstring --with-curl --prefix=/app/php-bin/DEBUG --with-config-file-path=/app/php-bin/DEBUG/etc --enable-fpm --with-fpm-user=work --with-fpm-group=work && \
    make -j$(nproc) && \
    make install && \
    cd /app/php-bin/DEBUG/etc && \
    mv /tmp/php.ini . && \
    mv php-fpm.d/www.conf.default php-fpm.d/www.conf && \
    mv /app/php-bin/DEBUG/etc/php-fpm.conf.default php-fpm.conf


COPY ["init.sh", "/init.sh"]
RUN useradd -m work && mkdir /home/work/scripts && chown work:work /home/work/scripts && chmod +x /init.sh
COPY ["index.php", "/home/work/scripts/"]
COPY ["flag", "/flag"]
COPY ["readflag.c", "/tmp/readflag.c"]
RUN cc /tmp/readflag.c -O2 -o /readflag && \
    chown root:root /flag /readflag && \
    chmod 0400 /flag && \
    chmod 4755 /readflag && \
    rm /tmp/readflag.c

CMD ["/init.sh"]
