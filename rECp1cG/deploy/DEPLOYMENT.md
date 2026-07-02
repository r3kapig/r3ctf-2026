# rECp1cG Remote Deployment

This directory contains the remote service deployment files for the challenge
`rECp1cG`.

## Files

- `Dockerfile`: builds the TCP challenge service image.
- `challenge.py`: per-connection challenge generator and answer verifier.
- `secret.py`: reads the flag from the `FLAG` environment variable.
- `docker-compose.yml`: local smoke-test deployment.
- `.dockerignore`: excludes local noise from Docker build context.
- `.env.example`: example environment variables for local deployment.

## Challenge Parameters

- `p_bits = 1024`
- `k = 21`
- `d_bits = 451`
- `Delta = 2^451`
- `solve_timeout = 888`
- exposed TCP port inside container: `9999`

Each TCP connection executes:

```bash
python -u challenge.py
```

The service prints a fresh public instance and waits for `P0.x`. If the answer
is correct, it prints `key_tag` and encrypted `ct`.

## Build And Run

```bash
docker compose up --build -d
```

Connect locally:

```bash
nc 127.0.0.1 9999
```

Use a custom host port:

```bash
PORT=10001 docker compose up --build -d
```

Set the deployment flag:

```bash
FLAG='r3ctf{real_flag_here}' docker compose up --build -d
```

Alternatively, copy `.env.example` to `.env` and edit `FLAG`.

## Base Image Note

The Dockerfile currently uses:

```dockerfile
FROM public.ecr.aws/ubuntu/ubuntu:24.04
```

This is a public Amazon ECR image and can be pulled without authentication when
the deployment environment allows access to `public.ecr.aws`.

If the platform only allows Docker Hub, replace the first line with:

```dockerfile
FROM ubuntu:24.04
```

If the platform has no public registry access, mirror Ubuntu 24.04 into the
platform's internal registry and replace the first line accordingly.

## Runtime Hardening

The compose file runs the service with:

- non-root user inside the image
- read-only root filesystem
- tmpfs for `/tmp`
- `no-new-privileges`
- `pids_limit`

The platform may override these settings with its own sandboxing policy.
