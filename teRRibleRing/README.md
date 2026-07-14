# teRRibleRing

- **Author:** 糖醋小鸡块
- **Submissions:** 230
- **Solves:** 4

## Description

Notice that there are 3 "R"s in the title :)

An RLWE-style distinguishing challenge. `task.sage` works in the polynomial ring `Z_p[x]/(f)` with `p = 0x8000000b` and `f` a degree-512 polynomial. For each bit of the flag it emits one sample pair `(a, b)`: for a `0` bit, `b = a*s + e mod f` with `s, e` drawn from a discrete Gaussian (`sigma = 5.0`); for a `1` bit, both `a` and `b` are uniform random. Players must analyze `samples.txt` to distinguish RLWE samples from uniform ones, recover the bit string, and decode it into the flag.

## Files

- `attachment/task.sage` — the SageMath script that generated the samples.
- `attachment/samples.txt` — the challenge output (the samples to analyze).

## Deployment

Static attachment — no remote service, no image. Players analyze `samples.txt` offline.

- **Flag:** `R3CTF{h0W_To_d3t3cT_Vu1n3r4bi1ity_0F_RING?}`
