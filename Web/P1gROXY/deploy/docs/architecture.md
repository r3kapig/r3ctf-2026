# Architecture

P1gROXY and WarehouseHub are separate processes deployed together.

## P1gROXY

P1gROXY is a native HTTP/1.1 reverse proxy. It accepts public client connections and forwards normalized requests to a configured localhost upstream.

Core modules:

- `http`: request/response parsing, chunked response decoding, header storage, and serialization.
- `content_coding`: gzip and deflate decoding through vendored mainstream zlib, including a small read-ahead stage for raw-deflate fragment adaptation.
- `policy`: request forwarding policy, response HTML URL normalization, hop-by-hop header removal, and browser security headers.
- `cache`: small memory cache for canonicalized cacheable responses.
- `socket`: TCP listener, upstream connection, timeouts, and complete-write helpers.

The response pipeline is:

1. Read upstream status line and headers.
2. Decode transfer framing when the upstream uses `Transfer-Encoding: chunked`.
3. Adapt response content coding when the upstream marks an encoded representation.
4. Normalize private upstream absolute URLs in HTML bodies.
5. Remove hop-by-hop headers and send browser-facing policy headers.

The proxy does not understand WarehouseHub business routes. It only applies generic HTTP edge policy.

## WarehouseHub

WarehouseHub is a thin Flask status portal. It exposes:

- `/` read-only HTML overview.
- `/status` read-only HTML status table.
- `/api/status` JSON status document.
- `/healthz` health check JSON.

The overview page is rendered by Flask and streamed by gunicorn as a deflate content-coded HTML response. The response writer keeps a short routing note in its stream so edge filters can make consistent policy decisions while still forwarding a complete decoded entity to the browser. This mirrors a common internal deployment where an upstream application emits compressed dynamic HTML while the edge proxy remains responsible for downstream policy and transformation.

WarehouseHub does not store business records or provide data-authoring workflows in this deployment.

## Deployment

The public network exposes only P1gROXY. WarehouseHub binds to `127.0.0.1` and receives normalized requests from the proxy.
