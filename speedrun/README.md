# speedrun

- **Category:** Misc (Minecraft)
- **Author:**
- **Difficulty:**
- **Wave:**
- **Points:**
- **Solves:**

## Description

Race through a custom Minecraft speedrun environment, defeat the dragon first, recover the hidden run code from The End, and turn that code into the real flag through the checker service. Warning: You only have 10 seconds to see the code, so be careful.

Version: 1.21.10

- Checker: ```nc challenge.ctf2026.r3kapig.com 30337```
- Server: ```challenge.ctf2026.r3kapig.com:30565```

All teams share **one** instance (one Paper server + one checker), so the flag
is derived per-team — see "Dynamic flag" below.

## Files

- `attachment/SpeedRunController.jar` — player handout (the speedrun plugin).
- `deploy/minecraft/` — Paper 1.21.10 server (`itzg/minecraft-server:java21`),
  the `SpeedRunController` + `AuthMe` plugins, and the random-seed start script.
- `deploy/checker/` — TCP checker (`socat` → `check_code.py`) that resolves the
  team token and emits the per-team flag.
- `deploy/shared/codes.json` — the pool of valid speedrun codes.
- `deploy/k8s.yaml` — single shared pod (minecraft + checker) + NodePort service.
- `deploy/docker-compose.yml` — local testing.

## Dynamic flag (per-team, shared container)

Because every team connects to the **same** checker, the flag is not baked into
the container. Instead the checker derives it from the player's **team token**:

1. Player connects to the checker (`nc <host> 30337`) and enters their team
   token (e.g. `9c-hK6cIA32dYmupaD0Bn`).
2. The checker queries the platform team API to resolve the token → `team_id`:
   `GET https://ctf2026.r3kapig.com/api/game/1/team/query?token=<token>`
   → `{"id": <team_id>, ...}`.
3. Player enters a valid speedrun code (must exist in `shared/codes.json`; codes
   are reusable and never consumed).
4. The checker returns the team's dynamic flag, generated with the same
   UUID-stego flag-gen the platform uses (`ret2shell-external-flag-gen`, see
   `reference/ret2shell-external-flag-gen/`):
   `r3ctf{encode_uuid(FLAG_TEMPLATE, FLAG_KEY, team_id)}`.

The `FLAG_TEMPLATE` / `FLAG_KEY` are baked into the checker image as env defaults
(and overridable via env). **The platform checker for this challenge must use the
identical template + key** so the flags the checker emits validate:

```text
FLAG_TEMPLATE = speedrun_mc_r3ctf_q6le8rxq
FLAG_KEY      = sBMu9o4ZIMWF9LusIYi8WlTc36JRMwN5
```

## Deployment

Production: apply `deploy/k8s.yaml` (one pod, one replica, shared by all teams):

```sh
kubectl apply -f deploy/k8s.yaml
```

- minecraft NodePort: **30565** (→ container 25565)
- checker NodePort: **30337** (→ container 31337)

Local testing:

```sh
cd deploy && ../infra.sh          # docker compose up --build -d
# minecraft on localhost:25565, checker on localhost:31337
printf '9c-hK6cIA32dYmupaD0Bn\nRUN-2F1A3D37A6B5B78CC0E2C89D\n' | nc localhost 31337
```

## Images

- `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/speedrun-minecraft:latest`
- `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/speedrun-checker:latest`

## Notes

- The Paper server resets the world and picks a fresh random seed on every
  container start (`RESET_WORLD_ON_START` / `RANDOMIZE_SEED_ON_START`). On first
  boot the `itzg` image downloads Paper + the vanilla server (needs egress).
- The checker needs egress to reach the platform team API
  (`ctf2026.r3kapig.com`).
- Codes are validated against `codes.json` but **not** consumed: the per-team
  flag already prevents flag sharing, and consuming codes would drain the pool
  in a shared container.
