# P1gROXY

This package contains two separate services:

- `services/proxy`: P1gROXY, a C++ HTTP/1.1 reverse proxy.
- `services/warehousehub`: WarehouseHub, a small internal Flask status portal.

P1gROXY is the public entry point. WarehouseHub binds to localhost and serves fixed operational status pages for the proxy to publish.

## Build

```sh
make
```

The proxy builds its private zlib dependency from `services/proxy/vendor/zlib`.

## Local Run

```sh
python3 -m venv services/warehousehub/.venv
. services/warehousehub/.venv/bin/activate
pip install -r services/warehousehub/requirements.txt
make
./deploy/run-local.sh
```

Defaults:

- P1gROXY: `0.0.0.0:8080`
- WarehouseHub: `127.0.0.1:15081`

## Service Boundary

WarehouseHub is intentionally small. It owns only read-only operational pages and health JSON.

P1gROXY owns the HTTP edge behavior: connection handling, hop-by-hop header policy, request content-coding normalization, upstream forwarding, response transfer parsing, response content-coding adaptation, HTML URL normalization, cache metadata, and browser-facing security headers.
