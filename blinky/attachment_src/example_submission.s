# example_submission.s -- a MINIMAL user-mode submission SKELETON (NOT the exploit).
#
# It only demonstrates the ABI + the local build/run pipeline: the kernel boots at
# 0x2000, drops to USER mode at the eret target 0x0c (here), your code runs, prints
# to the stdout MMIO, and stops the sim with "HALT\n". It does NOT recover the PAC
# tag or reach the flag at 0x2030 -- that is the actual challenge, left to you.
#
# Build + run locally:
#   ./build.sh example_submission.s        # -> example_submission.mem (USER region)
#   ./run_local.sh example_submission.mem  # splice local kernel -> memory.mem, run sim
# Expected output:  "example submission: user-mode OK" then "HALT".
    .set noreorder
    .section .boot, "ax"          # USER region [0, 0x2000) -- the whole submission
    .balign 4
    .org 0x0
_uexc:
    j    _uexc                    # 0x00: fault vector (a committed/loud fault lands here)
    nop
    .org 0x0c
__start_user:                     # 0x0c: eret target (USER mode) -- ABI entry
    li   $t0, 0x20000010          # stdout MMIO
    dla  $t1, msg
print:
    lb   $t2, 0($t1)
    beqz $t2, done
    nop
    sb   $t2, 0($t0)              # print the message one byte at a time
    daddiu $t1, $t1, 1
    j    print
    nop
done:
    dli  $t3, 0x0000000a544c4148  # "HALT\n" -> stops the simulator
    sd   $t3, 0($t0)
hang:
    j    hang
    nop
    .balign 8
msg:
    .asciiz "example submission: user-mode OK\n"
