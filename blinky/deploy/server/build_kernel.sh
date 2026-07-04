#!/usr/bin/env bash
# build_kernel.sh -- assemble the secret kernel image (kernel_template.mem) from
# kernel.s, baking in a flag but leaving the PAC key as a SENTINEL that server.py
# randomises per submission.
#
#   FLAG   the flag string to bake in           (default: R3CTF{TEST_FLGA})
#   OUT    output $readmemh image path          (default: ./kernel_template.mem)
#   AS/LD/OBJCOPY   MIPS64 cross-tools           (default: mips64el-linux-gnu-*)
#
# Requires the mips64el binutils (as/ld/objcopy) and python3. The flag is embedded
# safely (no shell/sed interpolation): it is escaped for a MIPS `.asciiz` literal.
#
# NB: the kernel image is produced with `objcopy -O binary` (EXACT bytes), NOT the
# project's objdump2dat.py -- that tool reconstructs bytes by DISASSEMBLING, which
# mangles a `.data` section (a data word that happens to decode as a multi-byte
# instruction corrupts the flag/key). objcopy is byte-accurate for code + data.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# NB: do NOT use `${FLAG:-R3CTF{TEST_FLGA}}` -- the flag's own '}' closes the
# parameter expansion early and a stray '}' gets appended to the flag.
FLAG="${FLAG-}"; [ -n "$FLAG" ] || FLAG='R3CTF{TEST_FLGA}'
OUT="${OUT:-$HERE/kernel_template.mem}"

# Auto-detect the mips64el cross-tool prefix (Arch: -gnu-, Debian: -gnuabi64-).
detect_prefix() {
    local p
    for p in mips64el-linux-gnu- mips64el-linux-gnuabi64- mips64-linux-gnu-; do
        command -v "${p}as" >/dev/null 2>&1 && { echo "$p"; return; }
    done
    echo "mips64el-linux-gnu-"
}
PREFIX="${TOOLCHAIN_PREFIX:-$(detect_prefix)}"
AS="${AS:-${PREFIX}as}"
LD="${LD:-${PREFIX}ld}"
OBJCOPY="${OBJCOPY:-${PREFIX}objcopy}"
KERNEL_BASE="${KERNEL_BASE:-8192}"  # 0x2000 = PAC_KERNEL_BASE (timing variant; script.ld places .text here)

for t in "$AS" "$LD" "$OBJCOPY" python3; do
    command -v "$t" >/dev/null 2>&1 || { echo "missing tool: $t" >&2; exit 1; }
done

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

# Safely substitute @FLAG@ -> $FLAG, escaping backslash and double-quote for the
# .asciiz literal; reject embedded newlines (they would truncate the string).
FLAG="$FLAG" python3 - "$HERE/kernel.s" "$work/kernel.s" <<'PY'
import os, sys
src, dst = sys.argv[1], sys.argv[2]
flag = os.environ["FLAG"]
if "\n" in flag or "\r" in flag:
    sys.exit("FLAG must not contain a newline")
esc = flag.replace("\\", "\\\\").replace('"', '\\"')
open(dst, "w").write(open(src).read().replace("@FLAG@", esc))
PY

"$AS" -mabi=64 -O0 -mips64r6 "$work/kernel.s" -o "$work/k.o"
"$LD" -m elf64ltsmip -T "$HERE/script.ld" "$work/k.o" -o "$work/k.elf"
"$OBJCOPY" -O binary "$work/k.elf" "$work/k.bin"

# flat binary (based at KERNEL_BASE) -> $readmemh, 64-byte lines, byte 63 first.
KERNEL_BASE="$KERNEL_BASE" python3 - "$work/k.bin" "$OUT" <<'PY'
import os, sys
data = open(sys.argv[1], "rb").read()
base = int(os.environ["KERNEL_BASE"])
LINE = 64
assert base % LINE == 0, "kernel base must be 64-byte aligned"
recs = {}
for off in range(0, len(data), LINE):
    chunk = data[off:off + LINE].ljust(LINE, b"\0")
    if any(chunk):                                  # skip all-zero lines
        la = (base + off) // LINE
        recs[la] = "".join("%02x" % b for b in reversed(chunk))
with open(sys.argv[2], "w") as f:
    for la in sorted(recs):
        f.write("@%08x\n%s\n" % (la, recs[la]))
PY
echo "built $OUT  (flag baked, PAC key = per-run SENTINEL)"
