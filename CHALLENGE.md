# R3CTF 2026 Challenges

Registry: `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/<name>:latest`

This file is the authoritative challenge / image / port / resource list.
Per-challenge details live in each `<challenge>/README.md`.

## Image list (needs build / push)

| Name | Image | CPU | Memory |
|---|---|---|---|
| ezvpn | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/ezvpn:latest` | 0.1 | 128m |
| HEuristic | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/heuristic:latest` | 0.5 | 256m |
| rECp1cG | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/recp1cg:latest` | 0.1 | 128m |
| P1gROXY | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/p1groxy:latest` | 0.1 | 128m |
| netshare | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/netshare:latest` | 0.5 | 256m |
| trustedhash | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/trustedhash:latest` | 1.0 | 2g |
| r3map | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3map:latest` | 2.0 | 3g |
| TsukisRhythmGame | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/tsukisrhythmgame:latest` | 0.1 | 128m |
| definitely-not-a-web-chal | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/definitely-not-a-web-chal:latest` | 0.5 | 256m |
| r3ticket | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3ticket:latest` | 1.0 | 512m |
| z3kapig | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/z3kapig:latest` | 2.0 | 1g |
| polys | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/polys:latest` | 0.5 | 128m |
| encrypted-activation | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/encrypted-activation:latest` | 1.0 | 512m |
| Mafuyuuuuu | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/mafuyuuuuu-{nginx,frontend,backend}:latest` (3 images, single pod) | ~1.7 | ~1.6g |
| Mafuyuuuuu-rev | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/mafuyuuuuu-rev-{nginx,frontend,backend}:latest` (3 images, single pod, revenge version) | ~1.7 | ~1.6g |
| escape-cet | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/escape-cet:latest` | 1.0 | 1g |
| inside | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/inside:latest` | 1.0 | 1g |
| r3reach | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3reach:latest` | 2.0 | 3g |
| speedrun | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/speedrun-{minecraft,checker}:latest` (2 images, one shared pod) | 2→6 | 4g→8g |
| blinky | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/blinky:latest` | 2.0 | 1g |
| minemaze | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/minemaze:latest` | 2.0 | 4g |
| r3chat | `registry.ctf2026.r3kapig.com/r3ctf_2026_6a511700/r3chat-{server,bot}:latest` (2 images, build source in `r3chat/src/`) | 1.0 / 2.5 | 512Mi / 2Gi |

## Local-run / attachment-only (no image push)

| Name | Notes |
|---|---|
| whisper | Local run only; no build/push. Deploy: `cd deploy/deploy && ./run.sh <public-ip> [N]` — `[N]` is the concurrent-device cap (extra teams queue); dynamic flag implemented. Needs KVM + Android AVD, 4 CPU / 6 GB per victim. |
| pewpew | Attachment only: `attachment/{to_player.zip, r3ctf-pewpew.rdp}` (Windows LFH; connects to an external Windows Server 2025 host). |
| Time Capsule | Attachment only: the forensics / steganography chain files under `attachment/`. |
| teRRibleRing | Attachment only: `attachment/{task.sage, samples.txt}` (Ring-LWE, SageMath, offline analysis). |
| lift | Attachment only: `attachment/chall` (static ELF; IR / lambda VM reversing, offline analysis). |
| funnygame | Attachment only: `attachment/FunnyGame.7z` (Unity IL2CPP game reversing, offline analysis). Static flag. |
| babycom | Deployed on the VM host (`vm.ctf2026.r3kapig.com`); no build/push. 16 QEMU/KVM Windows instances, ports 28300–28315, SSH login. Static flag `r3ctf{intended-flag-extraction-without-code-exec}`. Ops: `babycom/OPS.md`. |
| someday | Deployed on the VM host (`vm.ctf2026.r3kapig.com`); no build/push. 16 QEMU/KVM Windows instances, ports 28400–28415, SSH login. Static flag `r3ctf{pwn2own_for_the_win!!!!!!!}`. Ops: `someday/OPS.md`. |
| tap2pwn | Statement only + external attachment (Onetap v3 JS-engine RCE; single `.js` exploit, popcalc, 3 attempts per team, ticket submission). Static flag — see `tap2pwn/checker.rx`. |
| security-usage-intelligence | iOS pwn (sponsored by Nebula Security); started via ticket, 3-minute window, 3 attempts per team. Attachment `attachment/security_usage_intelligence.tar.gz`. Static flag — see `security-usage-intelligence/checker.rx`. |
| survey | Survey (1 point), Google Form: <https://forms.gle/D8tjSMxcEtuGovG6A>. Static flag (uppercase `R3CTF` prefix) — see `survey/checker.rx`. |
| sanity-check | Welcome/sanity challenge; the flag is published on the official Discord. Static flag — see `sanity-check/checker.rx`. |

## Notes

- **netshare** — the image is the per-team bridge pod (lightweight Flask). The controller (`kubernetes-on-demand-main/`) runs with `network_mode: host` + a `/var/run/docker.sock` mount and starts one kind cluster per team; give the controller host 2–4 GB RAM.
- **trustedhash** — the `trusted-hash-portal` image is ~7.57 GB. The player `nix-builder` dev image is a separate heavy Nix build, outside the registry.
- **whisper** — production currently runs on `vm.ctf2026.r3kapig.com` with 8 victim devices: `cd deploy/deploy && ./run.sh vm.ctf2026.r3kapig.com 8`.
- **ezvpn** — single-container deployment (the early internal `172.20.0.0/24` decoy network was removed). The entrypoint execs the binary directly instead of using ld-linux as the loader, to preserve ASLR entropy.
- **Mafuyuuuuu** — the pod nginx config (`nginx/nginx.pod.conf`) is baked into the nginx image, so the pod starts fine without the ConfigMap; `k8s.yaml` keeps the ConfigMap mount only as an override hook. Local compose instead volume-mounts `nginx/nginx.conf` (the service-name variant).
- **Mafuyuuuuu-rev** — differences vs Mafuyuuuuu: the backend adds a global, per-instance rate limit on the signal endpoint (HTTP 429; counted per instance, X-Forwarded-For rotation does not bypass it — PR#9), and the frontend adds a 2 s send cooldown. The dynamic-flag mechanism is unchanged.
- **speedrun** — per-run timeout `SPEEDRUN_RUN_TIMEOUT_SECONDS=3600`; `bukkit.yml` sets `connection-throttle: -1` so multiple players behind one IP / proxy / NAT are not throttled.

Build / push conventions (ops host only, macOS tar quirks, no parallel heavy builds): see `AGENTS.md` and `DEPLOY.md`.
