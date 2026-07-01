# Whisper - Local Stack

A self-contained local environment: the messaging backend plus one Android
device. The local `/flag.txt` holds a placeholder value.

## Requirements

- Linux x86_64 host with KVM (`ls /dev/kvm` must exist)
- Docker + Docker Compose v2, ~4 GB free RAM

## Run

```bash
./run.sh
```

First run downloads the Android SDK image (15-30 min); later runs are fast.
Backend (HTTP + WebSocket) is at `http://localhost:8000`, device handle
`victim`. Register an account on the backend to start using the app.

## Stop

```bash
docker compose down -v
```
