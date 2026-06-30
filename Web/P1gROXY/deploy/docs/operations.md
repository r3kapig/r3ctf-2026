# Operations

## Build

Run `make` from the package root. The proxy is built with CMake and the WarehouseHub Python modules are compile-checked.

## Configuration

P1gROXY is configured through `deploy/p1groxy.env`.

WarehouseHub is configured through `deploy/warehousehub.env`:

- `WAREHOUSEHUB_BIND`
- `WAREHOUSEHUB_WORKERS`
- `WAREHOUSEHUB_STREAM_COMPRESSED_HOME`
- `WAREHOUSEHUB_STREAM_COMPRESSION_LEVEL`
- `WAREHOUSEHUB_STREAM_CHUNK_BYTES`

The compressed overview route is streamed in multiple application chunks. P1gROXY may decode a compact fragment preview for policy checks while decoding the full entity for the downstream response.

## Runtime

`deploy/run-local.sh` starts WarehouseHub first and then execs P1gROXY. The container entrypoint follows the same two-process model with gunicorn for WarehouseHub.

## Logs

P1gROXY writes timestamped access and error logs to stderr. WarehouseHub/gunicorn writes access logs to stdout/stderr. The proxy does not log full HTTP bodies.
