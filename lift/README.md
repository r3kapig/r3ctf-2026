# lift

- **Category:** Reverse
- **Author:** 
- **Difficulty:** 
- **Wave:** 
- **Points:** 
- **Solves:** 

## Description

A static reverse-engineering challenge. The provided ELF binary lifts its input
into an internal IR / lambda-calculus VM; recover the expected input to extract
the flag.

## Flag

```
R3CTF{45m_l1ft_1R_l1ft_l4mbd4VM_r3v!!!}
```

## Files

- `attachment/chall` — stripped x86-64 ELF (PIE, dynamically linked). Static
  attachment; players reverse it offline.

## Deployment

Static attachment — no remote service, no image to build. Players download
`chall` and analyze it locally.
