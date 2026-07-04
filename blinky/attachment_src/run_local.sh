#!/usr/bin/env bash
# run_local.sh -- splice a USER submission with a kernel image and run the sim.
#
#   ./run_local.sh [submission.mem] [kernel.mem]
#
# Merges your USER region (< 0x2000) with the kernel (>= 0x2000) into ./memory.mem,
# then runs ./SOC_run_sim (reads ./memory.mem, prints stdout until HALT). Defaults to
# example_submission.mem + example_kernel.mem, so a bare `./run_local.sh` runs the
# shipped example. Build a submission first with:  ./build.sh exploit.s
#
# The local kernel has a FIXED key + fake flag (offline dev only); the server's key is
# per-run, so the tag you recover here is NOT the server's.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

find_file() {  # $1 = name: search cwd then the script's dir
    if [ -f "./$1" ]; then echo "./$1"; elif [ -f "$HERE/$1" ]; then echo "$HERE/$1"; fi
}

SUB="${1:-$(find_file example_submission.mem)}"
KMEM="${2:-$(find_file example_kernel.mem)}"
OUT="${OUT:-memory.mem}"
SIM="${SIM:-$(find_file SOC_run_sim)}"

[ -n "$SUB"  ] && [ -f "$SUB"  ] || { echo "submission image not found: ${1:-example_submission.mem}" >&2; exit 1; }
[ -n "$KMEM" ] && [ -f "$KMEM" ] || { echo "kernel image not found: ${2:-example_kernel.mem}" >&2; exit 1; }
command -v python3 >/dev/null 2>&1 || { echo "missing tool: python3" >&2; exit 1; }

# Merge: kernel owns lines >= 128 (>= 0x2000); submission owns lines < 128.
SUB="$SUB" KMEM="$KMEM" python3 - "$OUT" <<'PY'
import os, sys
KLINE = 0x2000 // 64   # 128
def load(path):
    toks = [t.strip() for t in open(path) if t.strip()]
    return {int(toks[i][1:], 16): toks[i + 1] for i in range(0, len(toks), 2)}
recs = {la: d for la, d in load(os.environ["KMEM"]).items() if la >= KLINE}   # kernel
recs.update({la: d for la, d in load(os.environ["SUB"]).items() if la < KLINE})  # user
with open(sys.argv[1], "w") as f:
    for la in sorted(recs):
        f.write("@%08x\n%s\n" % (la, recs[la]))
print("spliced %s (user) + %s (kernel) -> %s" %
      (os.path.basename(os.environ["SUB"]), os.path.basename(os.environ["KMEM"]), sys.argv[1]))
PY

if [ -n "$SIM" ] && [ -x "$SIM" ]; then
    echo "--- running $SIM (reads ./$OUT) ---"
    # SOC_run_sim reads ./memory.mem from its cwd; run it where $OUT lives.
    (cd "$(dirname "$OUT")" && exec "$SIM")
else
    echo "built $OUT -- SOC_run_sim not found/executable here; run it in this directory."
fi
