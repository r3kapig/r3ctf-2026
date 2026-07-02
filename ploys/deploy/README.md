# ploys deploy

Build and run:

```sh
docker compose -f deploy/docker-compose.yml up --build
```

The service exposes one raw TCP port, `1337`, backed by `socat` and `/app/ploys`.
The deploy image copies `attachments/ploys` directly so the public attachment and
the remote binary stay byte-for-byte identical.
