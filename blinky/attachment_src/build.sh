#!/usr/bin/env bash
# build.sh -- assemble a USER-mode submission into an uploadable image.
#
#   ./build.sh [src.s] [out_prefix]      # defaults: exploit.s, src basename
#
# Emits <out_prefix>.{bin,mem} = your USER region only (< 0x2000); upload either to
# the server, or run locally with:  ./run_local.sh <out_prefix>.mem
# Put code in `.section .boot,"ax"` below 0x2000; entry (eret target) is 0x0c.
# See README.md for the memory map.
#
# Toolchain-free via the provided Docker image:
#   docker build -t pacman-build .
#   docker run --rm -v "$PWD:/work" pacman-build exploit.s
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SRC="${1:-exploit.s}"
[ -f "$SRC" ] || { echo "no such source file: $SRC" >&2; exit 1; }
# default output prefix = source basename without extension
DEF_OUT="$(basename "$SRC")"; DEF_OUT="${DEF_OUT%.*}"
OUT="${2:-$DEF_OUT}"
LD_SCRIPT="${LD_SCRIPT:-$HERE/script.ld}"
[ -f "$LD_SCRIPT" ] || { echo "missing linker script: $LD_SCRIPT" >&2; exit 1; }

# Auto-detect the mips64el cross-tool prefix (Debian/Ubuntu: -gnuabi64-, Arch: -gnu-).
detect_prefix() {
    local p
    for p in mips64el-linux-gnuabi64- mips64el-linux-gnu- mips64-linux-gnu-; do
        command -v "${p}as" >/dev/null 2>&1 && { echo "$p"; return; }
    done
    echo "mips64el-linux-gnuabi64-"
}
PREFIX="${TOOLCHAIN_PREFIX:-$(detect_prefix)}"
AS="${AS:-${PREFIX}as}"
LD="${LD:-${PREFIX}ld}"
OBJCOPY="${OBJCOPY:-${PREFIX}objcopy}"

for t in "$AS" "$LD" "$OBJCOPY" python3; do
    command -v "$t" >/dev/null 2>&1 || { echo "missing tool: $t" >&2; exit 1; }
done

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

"$AS"      -mabi=64 -O0 -mips64r6 "$SRC" -o "$work/e.o"
"$LD"      -m elf64ltsmip -T "$LD_SCRIPT" "$work/e.o" -o "$work/e.elf"
"$OBJCOPY" -O binary "$work/e.elf" "$OUT.bin"

# raw user binary (@0x0) -> $readmemh: 64-byte lines, byte 63 first (byte 0 = low hex).
python3 - "$OUT.bin" "$OUT.mem" <<'PY'
import sys
LINE = 64
data = open(sys.argv[1], "rb").read()
recs = {}
for off in range(0, len(data), LINE):
    chunk = data[off:off + LINE].ljust(LINE, b"\0")
    if any(chunk):                                  # skip all-zero lines
        recs[off // LINE] = "".join("%02x" % b for b in reversed(chunk))
with open(sys.argv[2], "w") as f:
    for la in sorted(recs):
        f.write("@%08x\n%s\n" % (la, recs[la]))
PY

echo "built $OUT.bin and $OUT.mem (USER region @0x0)"
echo "  upload: $OUT.mem or $OUT.bin      run locally: ./run_local.sh $OUT.mem"
