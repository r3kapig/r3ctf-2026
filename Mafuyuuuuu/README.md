# Mafuyuuuuu

Mafuyuuuuu is a Project SEKAI themed .NET web challenge. The public service is a three-container stack:

- `nginx`: public reverse proxy on port `8089`
- `frontend`: Vite/Tailwind UI
- `backend`: ASP.NET Core API, `/flag`, and `/readflag`

## Deploy

```sh
./infra.sh
```

The service listens on `http://127.0.0.1:8089/`.

The test flag is stored at `deploy/deploy/flag`.

## Player Attachment

The player package is:

```text
attachment/to-player.zip
```

## Solve

```sh
python3 solve/solve.py http://127.0.0.1:8089
```
