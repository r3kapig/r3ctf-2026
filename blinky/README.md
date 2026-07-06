# blinky

- **Category:** Misc (hardware / microarchitecture)
- **Author:** Eritque arcus
- **Difficulty:** Medium
- **Wave:** 2
- **Points:**
- **Solves:**

## Description

A silicon startup is shopping around a *"secure by construction"* MIPS64r6 soft-core, and the marketing is bold: **even if you own the machine in user mode, you can never redirect control flow into our kernel.** Their proof of confidence is very straightforward, the routine that prints their crown-jewel flag sits at a **fixed, publicly documented kernel address**, and they'll happily boot *whatever user-mode code you send them*.

The magic word is **Pointer Authentication (PAC)**. Every indirect jump that lands in the kernel is checked by a hardware gate: a pointer forged without the secret key faults instead of jumping, and the gate stops answering after a few *loud* failures. No key is readable from user mode, and there is no instruction that will sign a pointer for you.

They shipped you the whole RTL to look at. They think that's safe.

Prove them wrong.

A kernel routine at a **known address** (`0x2030`) prints the flag, but you can't jump
to it: this 0dMIPS MIPS64r6 soft-core implements **Pointer Authentication (PAC)**. An
indirect jump from **user mode** into the **kernel region** `[0x2000, 0x100000)` is
authenticated against an **8-bit tag** in the pointer's top bits `[63:56]`. The tag key
lives in a CP0 register user code can't read and there is no signing instruction, so the
tag must be **recovered** — and a commit-time fault rate-limiter locks the gate after a
few *committed* PAC faults, so you can't brute-force it loudly.

The intended solve is a real **PACMAN / Spectre** attack purely over a **D-cache timing
side channel**: the core has a **PAC-gated load** gadget. Run it *speculatively* on a
mispredicted branch — a good tag fills a user-owned PROBE line, a bad tag is `NO_LOAD`
and, drained as speculative, never commits a fault. **Time** a PROBE reload to tell a
correct guess (cache hit) from a wrong one (miss); recover the 8-bit tag silently in a
single run, then `jr {tag,0x2030}` authenticates the gate and the kernel prints the flag.

Players get the full SoC RTL (the RTL key is a local placeholder) plus a container that builds
their MIPS assembly into an uploadable memory image; the kernel, flag, and per-run PAC
key stay on the server.

## Files

- `README.md` - this file (metadata + description).
- `infra.sh` - build + run helper (`build` / `run` / `local` / `health`).
- `attachment_src/` — **player handout**: the SoC RTL (PAC key is a local placeholder), `SOC_run_sim`,
  `Dockerfile` + `build.sh` (compile a `.s` into an uploadable USER-region `.mem`),
  `run_local.sh` (splice a submission `.mem` with a kernel `.mem` and run the sim),
  `script.ld`, a benign `example_submission.{s,mem}` scaffold, and `example_kernel.mem`
  (throwaway local kernel — fake flag, fixed offline key — for offline dev). Ships **no**
  example exploit and **no** real kernel/flag.
- `attachment/` - handout in zip
- `deploy/` - the live container: `Dockerfile`, `entrypoint.sh` (dynamic-flag bake), and
  `deploy/server/` (the runtime the image runs — `server.py`, `kernel.s`,
  `build_kernel.sh`, `script.ld`, `SOC_run_sim`) that splices the player upload under
  the per-run secret kernel.
- `solve/` - reference solver + healthcheck: `ref.s` (the reference exploit), `ref.mem`
  (its built image), `solve.py` (submits it), `healthcheck.sh`.

## Deployment

The flag is injected at runtime via the `FLAG` environment variable; the image bakes
only a placeholder. `deploy/entrypoint.sh` assembles the secret kernel with `$FLAG` at
container start, then scrubs `FLAG` from the environment. In addition, `server.py`
rewrites the kernel's PAC key with a **fresh random 64-bit value on every submission**,
so the correct 8-bit tag differs each run — a single-run timing sweep still solves it (it
sweeps all 2⁸ tags), but a leaked (pointer, tag) pair is worthless across runs.

Build context is the challenge root (the Dockerfile `COPY`s from `deploy/`):

```sh
./infra.sh build                       # docker build the server image
FLAG='r3ctf{...}' PORT=8080 ./infra.sh run
./infra.sh health                      # submit solve/ref.mem, expect a flag back

# no docker (host needs python3 + mips64el binutils):
PORT=8080 ./infra.sh local &
SERVER=http://127.0.0.1:8080 ./infra.sh health
```

- **Port:** container `8080` (HTTP), host `$PORT` (default `8080`)
- **Flag env:** `FLAG` (format `r3ctf{...}`, lowercase)
- `SOC_run_sim` is a **prebuilt x86-64** binary from the 0dMIPS SoC, built with
  `ENABLE_PAC`, `PAC_KERNEL_BASE=0x2000`, `PAC_PROBE_ADDR=0x1000`, `PAC_TAG_BITS=8`,
  `PAC_HANDLER_ADDR=0x80` (CMake `-DODMIPS_PAC_TAG_BITS=8 -DODMIPS_PAC_KERNEL_BASE=8192
  …`). It needs a new-enough glibc/libstdc++ (see the base-image note in
  `deploy/Dockerfile`); rebuild it if the RTL changes.

<!-- ## Hints

- Reverse the PAC gate and the **speculation window**: `attachment/rtl/units/core_EX.sv`,
  `attachment/rtl/modules/pac.sv`, and the branch predictor.
- Wrong guesses only fault if they **commit**. Keep them speculative and read the answer
  from cache timing, not from architectural state.
- The miss/hit latency is noisy (I$/D$ arbiter beat) — measure each guess more than once. -->

> `attachment/` is the only thing that goes to players. **Never** ship the kernel source
> or a real kernel image — the flag is injected at runtime and the kernel region is
> server-owned.
