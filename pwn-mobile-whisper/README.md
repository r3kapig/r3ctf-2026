# pwn-mobile-whisper

> Whisper — your messages stay private. Your phone, less so.

A production-grade Android messaging app on a custom AOSP/Cuttlefish image.

Flag format: `R3CTF{...}`

## Layout

- `server/` — hosted challenge infrastructure. A `docker compose` stack (proxy,
  backend, judge, and privileged Cuttlefish victim runners requiring `/dev/kvm`).
  Each team leases a fresh victim instance provisioned with a per-team dynamic
  flag. See `server/README.md` for deploy steps and KVM host requirements.
- `local-stack/` — the player handout. The APK plus a self-contained local
  device (placeholder flag) players use to develop their exploit offline before
  firing at the live target.

## Server deploy

KVM-capable host required.

```bash
cd server
./run.sh <public-ip> <num-instances>
```

The script auto-generates a secret flag key on first run, persists it to
`server/.flag_key` (gitignored), and prints it at startup. Set that same key in
the scoring platform's flag checker so per-team flags validate.

## Player device image

`local-stack/` needs `system.img` (~1.6 GB), the prebuilt local device. It is
too large for git, so it is hosted separately:

https://drive.google.com/drive/folders/1E7puSgXLNHnUFKPCSPcGwDNFS5kVXrdG?usp=sharing

Download it, place it at `local-stack/system.img` (or drop it beside the bundle
and run `local-stack/setup.sh`, which copies it in), then run
`local-stack/run.sh`.

The player handout is the `local-stack/` directory zipped together with this
`system.img`.
