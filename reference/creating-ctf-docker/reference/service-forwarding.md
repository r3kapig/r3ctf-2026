# Service forwarding reference

How players connect to the challenge process. Pick by **who owns the listening socket**.

## 1. xinetd (pwn / pyjail) — with chroot sandbox

`Dockerfile`:
```dockerfile
RUN apt-get install -y lib32z1 xinetd
COPY ./config/ctf.xinetd /etc/xinetd.d/ctf
RUN echo "Blocked by ctf_xinetd" > /etc/banner_fail
```

`config/ctf.xinetd` — chroot + drop to uid 1000:
```c
service ctf
{
    disable     = no
    socket_type = stream
    protocol    = tcp
    wait        = no
    user        = root
    type        = UNLISTED
    port        = 9999
    bind        = 0.0.0.0
    server      = /usr/sbin/chroot
    server_args = --userspec=1000:1000 /home/ctf ./attachment
    banner_fail = /etc/banner_fail
    per_source  = 10        # max concurrent instances per source IP
    rlimit_cpu  = 20        # CPU seconds per instance
    #rlimit_as  = 256M      # address-space limit
}
```

Start in entrypoint:
```sh
/etc/init.d/xinetd start
sleep infinity        # keep PID 1 alive; put cleanup BEFORE this line
```

**Jail tree** (build in Dockerfile for pwn):
```dockerfile
RUN useradd -m ctf && cp -R /usr/lib* /home/ctf
RUN mkdir /home/ctf/dev && \
    mknod /home/ctf/dev/null c 1 3 && mknod /home/ctf/dev/zero c 1 5 && \
    mknod /home/ctf/dev/random c 1 8 && mknod /home/ctf/dev/urandom c 1 9 && \
    chmod 666 /home/ctf/dev/*
RUN mkdir /home/ctf/bin && \
    cp /bin/sh /bin/ls /bin/cat /usr/bin/timeout /home/ctf/bin/
COPY ./src/attachment /home/ctf/attachment
RUN chown -R root:ctf /home/ctf && chmod -R 750 /home/ctf && \
    touch /home/ctf/flag && chmod 744 /home/ctf/flag
```
Note: Ubuntu ≥ 20.04 symlinks `/lib → /usr/lib`, so copy only `/usr/lib*`; 16.04/18.04 need `/lib*` + `/usr/lib*`. On arm64 the loader is `/lib/ld-linux-aarch64.so.1` and `cp -R /usr/lib*` yields only `/home/ctf/lib` (no `lib64`) — that is fine.

### xinetd without chroot (pyjail / simpler)
```c
service ctf
{
    ...
    user        = ctf
    port        = 9999
    server      = /usr/local/bin/python3
    server_args = -u /home/ctf/server.py
    per_source  = 10
    rlimit_cpu  = 20
}
```
Privilege drop via `user = ctf` (no chroot). Used by template `misc-pyjail-xinetd`.

### xinetd via `su` (when you need a shell wrapper)
```c
service ctf
{
    user        = root
    port        = 9999
    server      = /bin/su
    server_args = ctf -c /home/ctf/chall.sh
    rlimit_cpu  = 300
    cps         = 1 60     # 1 conn/sec, 60s penalty — throttles brute force
}
```
Seen in: r3ctf `aiseisei` (also adds a Proof-of-Work gate in `chall.sh`).

## 2. socat EXEC (crypto / pyjail / sagemath / compiled)

Simplest per-connection fork. `Dockerfile`:
```dockerfile
RUN apt-get install -y socat   # or: apk add --no-cache socat
```

Python session (no_socket):
```sh
socat -v -s TCP4-LISTEN:9999,tcpwrap=script,reuseaddr,fork \
      EXEC:"python3 -u /app/main.py",stderr
```

SageMath session:
```sh
socat TCP4-LISTEN:9999,tcpwrap=script,reuseaddr,fork \
      EXEC:"sage /home/sage/main.sage"
```

Compiled binary, dropping to a user:
```sh
socat -T600 TCP-LISTEN:5000,reuseaddr,fork,su=ctf \
      EXEC:/app/main,pty,echo=0,rawer
```

Drop privileges via `su` wrapper (when socat itself runs as root):
```sh
socat tcp-listen:1337,fork,reuseaddr,bind=0.0.0.0 \
      exec:"su ubuntu -c 'timeout 60 /pwn'",stderr
```

Raw pty mode (interactive REPL feel, no line buffering quirks):
```sh
socat TCP-L:11421,fork,reuseaddr \
      EXEC:"python3 ./server.py",pty,stderr,setsid,sane,raw,echo=0
```

Options that matter:
- `fork,reuseaddr` — concurrent connections.
- `,stderr` — merge the child's stderr into the session (lets players see errors).
- `su=<user>` — drop privileges per connection (socat ≥ 1.7.4).
- `-T <sec>` — idle timeout per connection.
- `max-children=1` — serialize connections (single-instance jails).

## 3. Direct / with_socket (web / quiz / blockchain proxy)

The app itself binds the port. The entrypoint just runs it.

Python http.server / socketserver:
```sh
python3 /app/main.py          # app calls TCPServer(("0.0.0.0", 8080), ...)
```

Flask:
```sh
cd /app && flask run -h 0.0.0.0 -p 8080
```

Java jar:
```sh
java -jar /app/app.jar
```

Apache / nginx + php-fpm:
```sh
php-fpm & nginx &             # or: apache2 -D FOREGROUND
tail -F /var/log/nginx/access.log /var/log/nginx/error.log
```

Go / Node:
```sh
./main server                 # Go
node /app/bot.js              # Node
```

Forking TCP quiz server (pure Python, no forwarder):
```python
class ForkedServer(socketserver.ForkingMixIn, socketserver.TCPServer): pass
ForkedServer(("0.0.0.0", 10002), Task).serve_forever()
```

## 4. nsjail / `pwn.red/jail` (untrusted code execution)

For challenges that run player-supplied code. Multi-stage:
```dockerfile
FROM golang:tip-bookworm AS base
# ... build app, COPY flag.txt, mv flag.txt /flag-$(md5sum ...).txt
COPY --chmod=555 app.py run

FROM pwn.red/jail
COPY --from=base / /srv
ENV JAIL_TIME=30 JAIL_MEM=500M JAIL_CPU=4000 JAIL_PIDS=100 \
    JAIL_TMP_SIZE=50M JAIL_CONNS_PER_IP=4
```
Compose needs privileges:
```yaml
services:
  sandbox:
    build: .
    ports: ["5000:5000"]
    privileged: true
```
Run untrusted code with a restricted env:
```python
subprocess.run(["go","run",filename],
               env={"PATH":"/usr/local/go/bin:/usr/sbin:/usr/bin:/sbin:/bin","HOME":dirname})
```
Seen in: r3ctf `nobrackets` (attachment variant).

## Port conventions

| Category | Container port | Host mapping (r3ctf style) |
|---|---|---|
| pwn / pyjail | 9999 (xinetd/socat) or 1337 (socat) | 30013, 30017 |
| crypto (py/sagemath) | 9999 (template) or 11421 (custom) | 10801, 30011 |
| web php/flask | 80 (php) / 8080 (flask) | 8080→80, 30018 |
| web node/koh | 5000 | 30019 |
| java | 8080 (jar) / container-defined | 8080 |
| blockchain EVM proxy | 8888 (anvil on internal 8545) | 8888 |
| solana validator | 8899 (RPC) / 9999 / 8900 | 3000x |
| forensics quiz | 10002 | 3000x |

`EXPOSE` is documentary — the real exposure comes from compose/infra `ports:` / `-p`. Keep them consistent.
