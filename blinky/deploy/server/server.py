#!/usr/bin/env python3
"""CTF infrastructure for the Blinky challenge (D-cache timing).

The player uploads their USER-mode exploit -- the memory region below the kernel
base (0x2000). The server splices it onto the SECRET kernel image (kernel.mem,
region >= 0x2000, which holds the reset entry, the kernel_flag printer, and the
flag string), runs the SoC simulator, and returns the program's stdout.

The player NEVER controls the kernel region (line >= 0x2000/64 = 128): every byte
at or above 0x2000 comes from the server's kernel.mem, so the flag is reachable
only by authenticating the PAC cross-region gate with the correct 8-bit tag -- the
intended solve (a speculative D-cache-timing brute-force; see the challenge README).

Stdlib only. Configure via env vars (see below). Run:  python3 server.py

  SIM         path to SOC_run_sim               (default: ./SOC_run_sim)
  KERNEL_MEM  path to the secret kernel image    (default: ./kernel.mem)
  HOST/PORT   listen address                     (default: 0.0.0.0:8080)
  TIMEOUT     per-submission wall-clock seconds   (default: 120)
  MAX_UPLOAD  max submission bytes                (default: 65536)
  MAX_CONC    max concurrent simulations          (default: 2)
  MAX_CYCLES  per-submission clock-cycle budget    (default: 5000000)
"""
import html
import http.server
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading

HERE = os.path.dirname(os.path.abspath(__file__))
SIM        = os.environ.get("SIM",        os.path.join(HERE, "SOC_run_sim"))
# The kernel is a TEMPLATE ($readmemh image) whose PAC key is a sentinel data word
# that we overwrite with a fresh random key on every run (see kernel.s /
# build_kernel.sh). KERNEL_MEM stays as a legacy fallback (fixed key) if no
# template is present.
KERNEL_TEMPLATE = os.environ.get("KERNEL_TEMPLATE",
                                 os.path.join(HERE, "kernel_template.mem"))
KERNEL_MEM = os.environ.get("KERNEL_MEM", os.path.join(HERE, "kernel.mem"))
HOST       = os.environ.get("HOST", "0.0.0.0")
PORT       = int(os.environ.get("PORT", "8080"))
TIMEOUT    = int(os.environ.get("TIMEOUT", "120"))
MAX_UPLOAD = int(os.environ.get("MAX_UPLOAD", str(64 * 1024)))
MAX_CONC   = int(os.environ.get("MAX_CONC", "2"))
# Deterministic per-submission clock-cycle budget, passed to SOC_run_sim as argv[1].
# Bounds runaway/spinning submissions independently of the wall-clock TIMEOUT (a
# spin now exits in a fraction of a second instead of holding a slot for TIMEOUT).
# The reference solve finishes in <~60k cycles, so this is ~80x headroom.
MAX_CYCLES = int(os.environ.get("MAX_CYCLES", str(5_000_000)))

LINE_SIZE   = 64
KERNEL_LINE = 0x2000 // LINE_SIZE  # 128 -- splice boundary; player owns lines < this (user region [0,0x2000))
MAX_OUTPUT  = 32 * 1024

# kernel.s seeds __pac_key_val with this 64-bit sentinel; we find that little-endian
# byte pattern in the image and replace it with a random key for every submission,
# so the correct PAC tag differs each run (yet a single-run sweep still solves it).
PAC_KEY_SENTINEL = 0xB16B00B5DEADC0DE

_sem = threading.Semaphore(MAX_CONC)

# ---- Player-facing ABI (kept in sync with solve/ref.s) -------------------------
ABI = """\
Your submission is the USER region only: loaded at 0x0, must fit below 0x2000.
Anything at >= 0x2000 is DISCARDED.

  entry (eret target) ..... 0x0c
  exception vector ........ 0x00
  FLAG / WIN .............. 0x2030

  stdout MMIO ............. 0x20000010  sb/sd a byte; sd "HALT\\n" stops the sim
  cycle counter MMIO ...... 0x20000000  lw to read the cycle count
  kernel region ........... [0x2000, 0x100000)

The RTL, full memory map, and a build container are in the challenge attachment."""

INDEX = """<!doctype html><meta charset=utf-8>
<title>Blinky CTF</title>
<style>body{{font:14px/1.5 monospace;max-width:820px;margin:2rem auto;padding:0 1rem}}
pre{{background:#f4f4f4;padding:1rem;overflow:auto;white-space:pre-wrap}}</style>
<h1>Blinky</h1>
<p>Upload your USER-region submission (a <code>memory.mem</code>, or a raw binary
loaded at 0x0). It's spliced under the secret kernel and run; stdout is returned.</p>
<form method=post action=/submit enctype=multipart/form-data>
  <input type=file name=f required> <button>submit</button>
</form>
<p>Or: <code>curl --data-binary @memory.mem http://HOST:PORT/submit</code></p>
<h2>ABI</h2><pre>{abi}</pre>
""".format(abi=html.escape(ABI))


def load_mem(path):
    """Parse a $readmemh file into {line_addr: 128-hex}."""
    recs = {}
    with open(path) as f:
        toks = [t.strip() for t in f if t.strip()]
    i = 0
    while i < len(toks):
        if not toks[i].startswith("@"):
            raise ValueError("expected @addr, got %r" % toks[i])
        recs[int(toks[i][1:], 16)] = toks[i + 1]
        i += 2
    return recs


def raw_to_recs(data):
    """Raw binary loaded at 0x0 -> {line_addr: 128-hex}, objdump2dat byte order
    (byte 63 first, byte 0 last within a 64-byte line)."""
    recs = {}
    for k in range((len(data) + LINE_SIZE - 1) // LINE_SIZE):
        chunk = data[k * LINE_SIZE:(k + 1) * LINE_SIZE].ljust(LINE_SIZE, b"\0")
        recs[k] = "".join("%02x" % b for b in reversed(chunk))
    return recs


def parse_submission(body):
    """Accept memory.mem text (starts with '@') or raw binary; return only the
    user-region records (line_addr < KERNEL_LINE). Kernel-region records in the
    upload are ignored (the kernel is server-owned)."""
    text = None
    try:
        text = body.decode("ascii")
    except UnicodeDecodeError:
        pass
    if text is not None and text.lstrip().startswith("@"):
        recs = {}
        toks = [t.strip() for t in text.splitlines() if t.strip()]
        i = 0
        while i < len(toks):
            if not toks[i].startswith("@"):
                raise ValueError("malformed memory.mem near %r" % toks[i][:32])
            la = int(toks[i][1:], 16)
            d = toks[i + 1]
            if len(d) != LINE_SIZE * 2 or not re.fullmatch(r"[0-9a-fA-F]+", d):
                raise ValueError("bad data line for @%x" % la)
            recs[la] = d.lower()
            i += 2
    else:
        recs = raw_to_recs(body)
    user = {la: d for la, d in recs.items() if la < KERNEL_LINE}
    if not user:
        raise ValueError("submission has no user-region (<0x2000) content")
    return user


def _replace_dword_le(recs, sentinel_le, newval_le):
    """Find the little-endian 8-byte `sentinel_le` in the image (recs map line ->
    128-hex, byte 63 first) and overwrite it in place with `newval_le`. Returns the
    line it patched, or None if the sentinel is absent."""
    for la in recs:
        asc = bytearray.fromhex(recs[la])[::-1]      # 64 bytes, ascending order
        idx = bytes(asc).find(sentinel_le)
        if idx >= 0:
            asc[idx:idx + 8] = newval_le
            recs[la] = bytes(reversed(asc)).hex()
            return la
    return None


def kernel_records():
    """The kernel image for one run: load the template and, if it carries the PAC
    key sentinel, replace it with a fresh random 64-bit key. Falls back to the
    fixed-key legacy kernel.mem if no template exists."""
    if os.path.exists(KERNEL_TEMPLATE):
        recs = load_mem(KERNEL_TEMPLATE)
        key = secrets.randbits(64)
        sentinel = PAC_KEY_SENTINEL.to_bytes(8, "little")
        if _replace_dword_le(recs, sentinel, key.to_bytes(8, "little")) is None:
            raise RuntimeError("PAC key sentinel not found in %s -- rebuild it with "
                               "build_kernel.sh" % KERNEL_TEMPLATE)
        if os.environ.get("PAC_LOG_KEY"):   # ops-only; never returned to players
            print("[pac] run key = 0x%016x" % key, file=sys.stderr, flush=True)
        return recs
    return load_mem(KERNEL_MEM)   # legacy fixed-key image


def run_submission(body):
    """Splice user submission onto the secret kernel, run the sim, return stdout."""
    user = parse_submission(body)
    combined = kernel_records()             # kernel owns line >= KERNEL_LINE
    combined.update(user)                   # player owns line <  KERNEL_LINE
    work = tempfile.mkdtemp(prefix="pac_ctf_")
    try:
        with open(os.path.join(work, "memory.mem"), "w") as f:
            for la in sorted(combined):
                f.write("@%08x\n%s\n" % (la, combined[la]))
        try:
            # errors="replace": a submission may print arbitrary (non-UTF-8) bytes to
            # the stdout MMIO; decode them lossily instead of raising UnicodeDecodeError
            # (a ValueError) that would surface to the player as a bogus "rejected".
            proc = subprocess.run([SIM, str(MAX_CYCLES)], cwd=work,
                                   capture_output=True, text=True,
                                   errors="replace", timeout=TIMEOUT)
            out = _clean(proc.stdout)
            if not out and proc.returncode != 0:
                # sim failed to run (e.g. missing shared libs / bad memory image) --
                # log it for ops; players still just see "(no output)".
                print("[sim] exited %d with no stdout; stderr: %s"
                      % (proc.returncode, (proc.stderr or "").strip()[:400]),
                      file=sys.stderr, flush=True)
            return out
        except subprocess.TimeoutExpired as e:
            partial = _clean(e.stdout.decode("utf-8", "replace") if isinstance(e.stdout, bytes)
                             else (e.stdout or ""))
            return "[timed out after %ds]\n%s" % (TIMEOUT, partial)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _clean(raw):
    """Strip Verilog $display (cache) noise + NULs, trim surrounding whitespace,
    cap size."""
    txt = re.sub(r"TOP\.[^\n]*\n?", "", raw or "").replace("\0", "")
    return txt.strip()[:MAX_OUTPUT]


def _extract_multipart(body, ctype):
    """Minimal multipart/form-data: return the first file part's raw bytes."""
    m = re.search(r"boundary=([^;]+)", ctype)
    if not m:
        return body
    boundary = ("--" + m.group(1).strip().strip('"')).encode()
    for part in body.split(boundary):
        head, _, data = part.partition(b"\r\n\r\n")
        if b"filename=" in head and data:
            return data.rsplit(b"\r\n", 1)[0]  # drop trailing CRLF before boundary
    return body


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body, ctype="text/plain; charset=utf-8"):
        blob = body.encode() if isinstance(body, str) else body
        # On errors we may not have drained the request body; don't keep-alive.
        if code >= 400:
            self.close_connection = True
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(blob)))
            self.end_headers()
            self.wfile.write(blob)
        except (BrokenPipeError, ConnectionResetError):
            self.close_connection = True

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._send(200, INDEX, "text/html; charset=utf-8")
        elif self.path == "/abi":
            self._send(200, ABI)
        else:
            self._send(404, "not found\n")

    def do_POST(self):
        if self.path != "/submit":
            return self._send(404, "not found\n")
        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_UPLOAD:
            return self._send(413, "upload must be 1..%d bytes\n" % MAX_UPLOAD)
        body = self.rfile.read(length)
        ctype = self.headers.get("Content-Type", "")
        if ctype.startswith("multipart/form-data"):
            body = _extract_multipart(body, ctype)
        if not _sem.acquire(timeout=2):
            return self._send(503, "server busy, retry shortly\n")
        try:
            out = run_submission(body)
        except ValueError as e:
            return self._send(400, "rejected: %s\n" % e)
        except Exception as e:  # noqa: BLE001 -- never leak a stack trace to players
            return self._send(500, "internal error: %s\n" % type(e).__name__)
        finally:
            _sem.release()
        self._send(200, out or "(no output)\n")

    def log_message(self, fmt, *args):  # quieter default logging
        pass


class Server(http.server.ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def main():
    if not os.path.exists(SIM):
        raise SystemExit("missing required file: %s" % SIM)
    if not os.access(SIM, os.X_OK):
        raise SystemExit("sim not executable: %s" % SIM)
    if os.path.exists(KERNEL_TEMPLATE):
        kernel, mode = KERNEL_TEMPLATE, "per-run random PAC key"
    elif os.path.exists(KERNEL_MEM):
        kernel, mode = KERNEL_MEM, "legacy fixed PAC key"
    else:
        raise SystemExit("missing kernel image: %s (or legacy %s) -- run "
                         "build_kernel.sh" % (KERNEL_TEMPLATE, KERNEL_MEM))
    srv = Server((HOST, PORT), Handler)
    print("serving Blinky CTF on http://%s:%d  (sim=%s, kernel=%s, %s)"
          % (HOST, PORT, SIM, kernel, mode))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
