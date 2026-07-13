# Security Usage Intelligence

- **Category:** Pwn (iOS)
- **Author:** Nebula Security ([@nebusecurity](https://x.com/nebusecurity))
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

You know there will be an iOS challenge as this is R3CTF.

This challenge is from Nebula Security ([@nebusecurity](https://x.com/nebusecurity)).

Pack your exploit into a regular, installable **IPA** file and **open a
ticket** to start the challenge. You have **3 minutes** to pwn it; during the
attempt you can request any form of restart or environment reset. Verify
beforehand that your exploit works reliably and displays the flag on screen —
each team is limited to **3** attempts.

The flag is at `/var/jb/var/root/flag` (`-r-------- 1 root wheel`) on a
jailbroken iOS target. The sandbox profile is configured so the service in
the attachment is reachable from within the iOS sandbox.

## Files

- `attachment/security_usage_intelligence.tar.gz` — player handout (the
  target service / environment material to analyze before writing the IPA).
- `checker.rx` — platform flag checker (static flag), copied from the
  ret2shell export.

## Deployment

No container in this repo — the iOS target environment is operated by the
organizers and started per team via ticket (3-minute window, resets on
request, 3 attempts per team). Platform score rule: initial 1000 /
minimum 100 / decay 30.

- **Flag:** `r3ctf{s3curity_u5aGe_intEll1gence_secUre_unb3lievable_int3grity_securely_unBr3akably_impr3ssive}`
  (static; see `checker.rx`)
