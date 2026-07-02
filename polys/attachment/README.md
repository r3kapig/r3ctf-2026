# polys

Run locally with Docker:

```sh
docker compose up --build
```

The service listens on TCP port `1337`.

Included files:

- `polys`: challenge binary
- `libc.so.6`: matching Ubuntu 24.04 amd64 libc
- `ld-linux-x86-64.so.2`: matching dynamic loader
- `Dockerfile`, `docker-compose.yml`, `start.sh`: local challenge runner

The binary keeps function symbols for easier reversing, but debug/type metadata
and the layout globals (`foo`, `polys`, `poly_degrees`) are stripped.
