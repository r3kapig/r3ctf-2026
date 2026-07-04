# kernel.s -- server-side SECRET kernel for the 0dMIPS Blinky CTF.
#
# This is a piece of the 0dMIPS SoC's own program image (MIPS64r6 assembly). It
# occupies the KERNEL region (>= 0x2000) and is spliced over the player's user
# region by server.py. It boots in KERNEL mode at 0x2000, installs a PAC key into
# CP0 register 22, drops to USER mode at the fixed ABI entry 0x0c, and -- only if
# an indirect jump authenticates the PAC gate at 0x2030 -- prints the flag.
#
# Unlike a purely architectural silent-PAC approach, here the PAC gate is
# reached only by RECOVERING the tag through a D-cache TIMING side channel: the
# tag width is 8 bits and the intended solve times a speculative PAC-gated LOAD.
#
# Two things are parameterised so every instance / run is different:
#
#   * @FLAG@         -- the flag string, substituted at build/deploy time from the
#                       $FLAG env var (dynamic flag). The image bakes only a
#                       placeholder; the deploy entrypoint rebuilds with the real
#                       flag and scrubs the env.
#
#   * __pac_key_val  -- an 8-byte data word seeded with a recognizable SENTINEL.
#                       server.py overwrites it with a FRESH RANDOM 64-bit key for
#                       EVERY submission, so the correct PAC tag differs each run.
#                       Because the reference exploit sweeps all 2^8 tags in a
#                       single run, the challenge stays solvable for any key.
#
# The core lets kernel-mode code write CP0 reg22 (see src/units/cp0.sv); user code
# can neither read it back nor sign a pointer, so the tag can only be recovered
# through the speculative timing oracle -- that is the whole challenge.

    .text
    .global __start
__start:                          # 0x2000: reset entry (KERNEL mode)
    j    real_boot                #         skip the flag printer; go set up + eret
    nop

    .org 0x30                     # pin the WIN target to exactly 0x2030 (ABI)
    .global kernel_flag
kernel_flag:                      # 0x2030: reached only with the CORRECT PAC tag
    dla  $t1, flag_str
    li   $t0, 0x20000010          # stdout MMIO
kf_loop:
    lb   $t2, 0($t1)
    beqz $t2, kf_halt
    nop
    sb   $t2, 0($t0)              # print flag one byte at a time
    daddiu $t1, $t1, 1
    j    kf_loop
    nop
kf_halt:
    dli  $t3, 0x0000000a544c4148  # "HALT\n" -> stops the simulator
    sd   $t3, 0($t0)
kf_hang:
    j    kf_hang
    nop

real_boot:                        # boot tail, placed past the flag printer so the
                                  # flag printer can stay pinned at 0x2030
    dla  $t2, __pac_key_val
    ld   $t0, 0($t2)             # load the per-run PAC key (patched data word)
    mtc0 $t0, $22                # install it into CP0 reg22 (kernel-only write)

    # -- scrub key material before dropping to USER mode --------------------
    # We just pulled the PAC key through the D-cache, so a key-bearing line is
    # now resident (and the plaintext key still sits at __pac_key_val). Wipe the
    # memory word and writeback+invalidate BOTH ways of its D-cache set so no key
    # line survives into user mode.
    sd   $zero, 0($t2)           # zero the plaintext key word (updates its cache line)
    li   $t3, 0x800              # bit 11 = D-cache way select (2 ways x 32 sets)
    cache 0x1, 0($t2)            # WB_INVALIDATE key set, way = addr[11]  (DCACHE)
    daddu $t2, $t2, $t3          # flip to the other way
    cache 0x1, 0($t2)            # WB_INVALIDATE the other way of the key set

    li   $t0, 0x0c               # fixed ABI user entry (the eret target)
    mtc0 $t0, $14                # EPC = 0x0c
    # Status = KSU=10 (user) | EXL=1, IE=0 / IM=0. Interrupts MUST be masked: the
    # reset Status has IE=1 & IM=0xff, and the player's long timing sweep would
    # otherwise be aborted by a timer interrupt. Build Status fresh (do NOT inherit).
    ori  $t1, $zero, 0x12
    mtc0 $t1, $12
    ehb
    eret                          # drop to USER mode @ 0x0c -> player's code

    .data
    .balign 8
    .global __pac_key_val
__pac_key_val:
    .dword 0xB16B00B5DEADC0DE     # SENTINEL -- server.py overwrites per submission
    .global flag_str
flag_str:
    .asciiz "@FLAG@\n"
