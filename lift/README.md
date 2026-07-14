# lift

- **Author:** Merrg1n
- **Submissions:** 239
- **Solves:** 52

## Description

Disclaimer: No barbells were harmed or required in the solving of this challenge.

`chall` is a stripped, PIE, dynamically linked x86-64 ELF binary that prompts
`Input flag:` and validates the player's input. The flag is static — it is
recovered entirely by reversing the binary offline (per the flag text, the
intended solve involves a "lambda VM" implemented inside the binary). There is
no remote service; players download the attachment and analyze it locally.

## Files

- `attachment/chall` — stripped x86-64 ELF (PIE, dynamically linked) flag-checker binary; the player handout.
- `infra.sh` — no-op script noting this is a static attachment challenge (no image, no service).

## Deployment

Static attachment — no remote service, no image to build. Players download
`chall` and analyze it locally.

- **Flag:** `R3CTF{45m_l1ft_1R_l1ft_l4mbd4VM_r3v!!!}` (static, recovered by reversing the binary)
