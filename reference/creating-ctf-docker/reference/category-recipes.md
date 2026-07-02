# Category recipes

Minimal end-to-end skeletons. Copy the closest one, then adjust flag delivery (see `flag-injection.md`) and sandbox. For a fuller scaffold with `config/`+`service/`+`src/`+`docker/`, copy the matching folder under `ctf-docker-template/`.

---

## Pwn — xinetd + chroot

`Dockerfile`:
```dockerfile
FROM ubuntu:22.04
# lib32z1 is x86-only (32-bit i386 support); drop it on arm64 or for a native 64-bit binary
RUN apt-get update && apt-get install -y lib32z1 xinetd && rm -rf /var/lib/apt/lists/*
RUN useradd -m ctf
WORKDIR /home/ctf
RUN cp -R /usr/lib* /home/ctf
RUN mkdir /home/ctf/dev && \
    mknod /home/ctf/dev/null c 1 3 && mknod /home/ctf/dev/zero c 1 5 && \
    mknod /home/ctf/dev/random c 1 8 && mknod /home/ctf/dev/urandom c 1 9 && \
    chmod 666 /home/ctf/dev/*
RUN mkdir /home/ctf/bin && cp /bin/sh /bin/ls /bin/cat /usr/bin/timeout /home/ctf/bin/
COPY config/ctf.xinetd /etc/xinetd.d/ctf
RUN echo "Blocked by ctf_xinetd" > /etc/banner_fail
COPY service/docker-entrypoint.sh /
COPY src/attachment /home/ctf/attachment
# create the flag placeholder BEFORE chown so it is owned root:ctf (group-readable);
# `touch` after `chown` would leave it root:root (works for 744, breaks stricter perms)
RUN touch /home/ctf/flag && \
    chown -R root:ctf /home/ctf && chmod -R 750 /home/ctf && \
    chmod 744 /home/ctf/flag
EXPOSE 9999
ENTRYPOINT ["/bin/sh","/docker-entrypoint.sh"]
```

> **Architecture note:** the chroot lib-copy (`cp -R /usr/lib*`) is arch-agnostic, but the loader path and whether `lib64` exists are not. On x86_64 the interpreter is `/lib64/ld-linux-x86-64.so.2` and the copy yields `/home/ctf/lib64`; on arm64 it is `/lib/ld-linux-aarch64.so.1` with only `/home/ctf/lib`. `lib32z1` exists only on x86 — remove it for arm64 or a native 64-bit binary.
`service/docker-entrypoint.sh`:
```sh
#!/bin/sh
user=$(ls /home)
# FLAG resolve+scrub here (see flag-injection.md)
echo "$INSERT_FLAG" | tee /home/$user/flag
chmod 711 /home/ctf/attachment
/etc/init.d/xinetd start
sleep infinity
```
`config/ctf.xinetd`: see `service-forwarding.md` §1 (chroot `--userspec=1000:1000 /home/ctf ./attachment`). Binary in `src/` **must be named `attachment`** (or rename in Dockerfile + xinetd + entrypoint). Provide players an `attachment/` zip with the binary + matching `libc.so.6` + `ld-linux*.so.2` and a placeholder flag.

---

## Crypto Python — socat no_socket

`Dockerfile`:
```dockerfile
FROM python:3.10.13-slim-bullseye
RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir pycryptodome   # add your deps
COPY ./src/ /app
COPY ./service/docker-entrypoint.sh /app/docker-entrypoint.sh
RUN chmod +x /app/docker-entrypoint.sh
RUN useradd -m ctf && chown ctf:ctf /app
USER ctf
EXPOSE 9999
ENTRYPOINT ["/bin/sh","/app/docker-entrypoint.sh"]
```
`service/docker-entrypoint.sh`:
```sh
#!/bin/sh
rm -f /app/docker-entrypoint.sh
socat TCP4-LISTEN:9999,tcpwrap=script,reuseaddr,fork EXEC:"python3 -u /app/main.py",stderr
```
`src/main.py` reads `flag = os.getenv("FLAG")` and prints it on success. File **must be `main.py`**. Use `with_socket` variant (no socat, script binds its own socket) only if the challenge needs a custom protocol.

---

## Crypto SageMath — socat no_socket

`Dockerfile`:
```dockerfile
FROM sagemath/sagemath:9.6
USER root
RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*
USER sage
RUN sage --python -m pip install --no-cache-dir pycryptodome gmpy2
COPY ./src/main.sage /home/sage
COPY ./service/docker-entrypoint.sh /home/sage/docker-entrypoint.sh
EXPOSE 9999
ENTRYPOINT ["/bin/sh","/home/sage/docker-entrypoint.sh"]
```
`service/docker-entrypoint.sh`:
```sh
#!/bin/sh
rm -f /home/sage/docker-entrypoint.sh
socat TCP4-LISTEN:9999,tcpwrap=script,reuseaddr,fork EXEC:"sage /home/sage/main.sage"
```
File **must be `main.sage`**; reads `flag = os.getenv("FLAG")`. Runs as `sage`.

---

## Web PHP — nginx + php-fpm, flag file

`Dockerfile`:
```dockerfile
FROM php:7.3-fpm-alpine
RUN apk add --no-cache nginx bash
COPY config/nginx.conf /etc/nginx/nginx.conf
COPY src /var/www/html
RUN chown -R www-data:www-data /var/www/html
COPY service/docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh
WORKDIR /var/www/html
EXPOSE 80
ENTRYPOINT ["/docker-entrypoint.sh"]
```
`service/docker-entrypoint.sh`:
```sh
#!/bin/sh
rm -f /docker-entrypoint.sh
# FLAG resolve+scrub here
echo "$INSERT_FLAG" | tee /flag
chmod 744 /flag
php-fpm & nginx &
tail -F /var/log/nginx/access.log /var/log/nginx/error.log
```
For SQLi, switch to DB-row flag delivery and add `mysql` (copy `web-lnmp-php73`/`web-lamp-php80`). For a harder challenge, set `disable_functions`/`open_basedir` and add a `setuid /readflag`.

---

## Web Flask — flag file

`Dockerfile`:
```dockerfile
FROM python:3.10-slim-bullseye
RUN python3 -m pip install --no-cache-dir flask   # add your deps
COPY ./src/ /app
COPY ./service/docker-entrypoint.sh /
EXPOSE 8080
ENTRYPOINT ["/bin/sh","/docker-entrypoint.sh"]
```
`service/docker-entrypoint.sh`:
```sh
#!/bin/sh
# FLAG resolve+scrub here
echo "$INSERT_FLAG" | tee /flag
chmod 744 /flag && chmod 740 /app/*
cd /app && flask run -h 0.0.0.0 -p 8080
```
`src/app.py` exposes the intended vuln; keep `/flag` reachable only via that vuln. Main file **must be `app.py`**.

---

## Misc pyjail — socat EXEC, world-readable flag

`Dockerfile`:
```dockerfile
FROM python:3.10.12-slim-bullseye
RUN apt-get update && apt-get install -y socat && rm -rf /var/lib/apt/lists/*
RUN python3 -m pip install --no-cache-dir pycryptodome
RUN useradd -m ctf
WORKDIR /home/ctf
COPY src/server.py /home/ctf/server.py
COPY service/docker-entrypoint.sh /
EXPOSE 9999
ENTRYPOINT ["/bin/sh","/docker-entrypoint.sh"]
```
`service/docker-entrypoint.sh`:
```sh
#!/bin/sh
# FLAG resolve+scrub here
echo "$INSERT_FLAG" | tee /flag
chmod 744 /flag
socat TCP4-LISTEN:9999,tcpwrap=script,reuseaddr,fork EXEC:"python3 -u /home/ctf/server.py",stderr
```
Escape the jail → `cat /flag`. File **must be `server.py`**. For a harder jail, add chroot (`setcap CAP_SYS_CHROOT=+ep $(which python3)` + `os.chroot`) or run under `pwn.red/jail`.

---

## Misc quiz / forensics — forking TCP, env flag

`Dockerfile`:
```dockerfile
FROM python:3-alpine
WORKDIR /opt/challenge
COPY server.py answers.json .
EXPOSE 10002
CMD ["python","-u","server.py"]
```
`server.py` uses `socketserver.ForkingMixIn` on `0.0.0.0:10002`, optional Proof-of-Work, then `os.environ.get("FLAG", "...")` printed when all answers are correct. Keep `EXPOSE` and the bind port identical. No sandbox user needed (isolation = container-per-player).

---

## Blockchain EVM — foundry + FastAPI proxy

`Dockerfile`:
```dockerfile
FROM python:3.11-slim
RUN apt-get update && apt-get install -y curl git socat && rm -rf /var/lib/apt/lists/*
RUN curl -L https://foundry.paradigm.xyz | bash && /root/.foundry/bin/foundryup
ENV PATH="/root/.foundry/bin:${PATH}"
COPY deploy/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY deploy/project /project
RUN cd /project && forge build --out /artifacts/out --cache-path /artifacts/cache
COPY deploy/init.py deploy/proxy.py /
RUN useradd -m -u 1000 user
EXPOSE 8888
ENTRYPOINT ["/entrypoint.sh"]
```
`entrypoint.sh`:
```sh
#!/bin/sh
python3 -u /init.py &            # starts anvil on 127.0.0.1:8545, deploys, writes /deploy.txt + /user.txt
uvicorn proxy:app --host 0.0.0.0 --port 8888
```
`proxy.py` allowlists JSON-RPC namespaces (`web3/eth/net`), blocks `eth_sendTransaction`, and on `GET /` returns the flag only when `isSolved()` is true (see `flag-injection.md` §7). Use `forge-ctf`'s `CTFDeployment` for the standard setup/player flow, or a plain `forge-std` script that writes `instance_details.json`. Isolation = one container per player, each with its own anvil + fixed mnemonic.

---

## docker-compose.yml (local test)

```yaml
version: '3'
services:
  chall:
    build: ../
    environment:
      FLAG: "r3ctf{local_test_flag}"
    ports:
      - "9999:9999"
    restart: unless-stopped
```

## infra.sh (registry deploy)

```sh
#!/bin/sh
NAME=mychal
REG=registry.example.com/ctf2025
docker build . -t "$REG/$NAME:v0"
docker push "$REG/$NAME:v0"
docker run --rm -d -e FLAG='r3ctf{real}' \
  --cpus "0.1" --memory "128m" \
  -p 30001:9999 "$REG/$NAME:v0"
```
