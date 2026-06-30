# Whisper CTF - Server Deployment

## Prerequisites

- Linux x86_64 host with KVM (`ls /dev/kvm` must exist)
- Docker + Docker Compose v2

## Run

```bash
./run.sh <public-ip> [N]
```

`<public-ip>` is the address players use to reach the server. `[N]` is the
number of victim instances (default 2). First run downloads the Android SDK
image (15-30 min); later runs are fast. Set a real flag with
`WHISPER_REAL_FLAG='R3CTF{...}' ./run.sh ...`.

On startup `run.sh` prints a `WHISPER_FLAG_KEY`. Set that same value in your
scoring platform's flag checker and keep it secret.

Ports: judge UI/API `31337`, backend `31338`.

## Stop

```bash
docker compose down -v --remove-orphans
```
