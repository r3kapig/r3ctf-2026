#!/usr/bin/env python3
import argparse
import os
import sys
from functools import lru_cache
from pathlib import Path
from pwn import context, log, process, remote
from sage.all import GF, Matrix, PolynomialRing, RealField, ZZ, factorial, floor, lcm, vector


if hasattr(sys, "set_int_max_str_digits"):
    sys.set_int_max_str_digits(0)

N = 128
SHIFT = 1000
X_BITS = 26
XBOUND = 2**X_BITS
RECOVERY_PRIMES = (65537, 1000003, 1000000007, 1000000009)
EXACT_SCAN_LIMIT = 5000
LOG_SCAN_LIMIT = 100000
LOG2_10 = 3.3219280948873626


def lcm_upto(n):
    out = ZZ(1)
    for i in range(1, n):
        out = lcm(out, i)
    return out


L = lcm_upto(N)
D = factorial(N - 1)
OT_BASE = L * (ZZ(2) ** SHIFT)
QUERY_INDEX = -OT_BASE


def real_field(decimal_digits, guard=160):
    return RealField(int((decimal_digits + guard) * LOG2_10) + 64)


def leading_exact(value, digits):
    s = str(value)
    if len(s) < digits:
        s += "0" * (digits - len(s))
    return s[:digits]


def leading_from_log(log_value, digits, rf=None):
    if rf is None:
        rf = log_value.parent()

    frac = log_value - floor(log_value)
    if frac < 0:
        frac += 1

    lead = int(floor((rf(10) ** (frac + digits - 1))))
    if lead >= 10**digits:
        lead = 10**digits - 1
    s = str(lead)
    if len(s) < digits:
        s = s.zfill(digits)
    return s[:digits]


def balanced_digits(z, base, n):
    z = ZZ(z)
    base = ZZ(base)
    digits = []

    for _ in range(n):
        r = z % base
        if r > base // 2:
            r -= base
        digits.append(int(r))
        z = (z - r) // base

    if z:
        raise ValueError("base expansion did not terminate cleanly")
    return digits


@lru_cache(maxsize=None)
def build_matrix_mod(p):
    field = GF(p)
    ring = PolynomialRing(field, "q")
    q = ring.gen()
    rows = [[field(0)] * N for _ in range(N)]

    for i in range(N):
        poly = ring(1)

        for j in range(N):
            if i == j:
                continue

            if j < i:
                dist = i - j
                a = -field(1) / field(dist)
                b = -((j + dist - 1) // dist)
            else:
                dist = j - i
                a = field(1) / field(dist)
                b = j // dist

            poly *= a * q + field(b)

        poly *= field(D)
        for k, coeff in enumerate(poly.list()):
            rows[k][i] = coeff

    return Matrix(field, rows)


def recover_nums(ot_value):
    coeffs = balanced_digits(D * ZZ(ot_value), OT_BASE, N)

    for p in RECOVERY_PRIMES:
        field = GF(p)
        rhs = vector(field, [c % p for c in coeffs])

        try:
            sol = build_matrix_mod(p).solve_right(rhs)
        except (ArithmeticError, ValueError):
            continue

        nums = [int(ZZ(x)) for x in sol]
        if all(0 <= x < 2**16 for x in nums):
            return nums

    raise RuntimeError("failed to recover nums")


def exact_small_x(nums, prefix, limit=EXACT_SCAN_LIMIT):
    vals = [1] * len(nums)

    for x in range(limit):
        if leading_exact(sum(vals), len(prefix)) == prefix:
            return x
        vals = [v * a for v, a in zip(vals, nums)]

    return None


def leading_prefix_logsum(nums, x, digits):
    if x == 0:
        return leading_exact(len(nums), digits)

    rf = real_field(digits, guard=240)
    m = max(nums)
    mm = rf(m)
    total = rf(0)

    for a in nums:
        if a:
            total += (rf(a) / mm) ** x

    log_h = rf(x) * mm.log10() + total.log10()
    return leading_from_log(log_h, digits, rf)


def prefix_ok(nums, x, prefix):
    return leading_prefix_logsum(nums, x, len(prefix)) == prefix


def scan_x_logsum(nums, prefix, start=EXACT_SCAN_LIMIT, stop=LOG_SCAN_LIMIT, max_x=None):
    if max_x is None:
        max_x = XBOUND

    digits = len(prefix)
    rf = real_field(digits, guard=240)
    m = max(nums)
    mm = rf(m)
    log_m = mm.log10()
    ratios = [rf(a) / mm if a else rf(0) for a in nums]
    powers = [r**start for r in ratios]

    for x in range(start, min(stop, max_x)):
        total = sum(powers, rf(0))
        log_h = rf(x) * log_m + total.log10()

        if leading_from_log(log_h, digits, rf) == prefix:
            return x

        powers = [power * ratio for power, ratio in zip(powers, ratios)]

    return None


def frac01(value):
    value -= floor(value)
    if value < 0:
        value += 1
    return value


def round_div(num, den):
    if den < 0:
        num = -num
        den = -den

    if num >= 0:
        return (num + den // 2) // den
    return -((-num + den // 2) // den)


def closest_lattice_vector_2d(basis, target, radius=16):
    rows = [[int(basis[i, j]) for j in range(2)] for i in range(2)]
    (a, b), (c, d) = rows
    t0, t1 = map(int, target)
    det = a * d - b * c

    if det == 0:
        raise ValueError("singular lattice basis")

    center0 = round_div(t0 * d - t1 * c, det)
    center1 = round_div(a * t1 - b * t0, det)
    best = None
    best_dist = None

    for c0 in range(center0 - radius, center0 + radius + 1):
        for c1 in range(center1 - radius, center1 + radius + 1):
            v0 = c0 * a + c1 * c
            v1 = c0 * b + c1 * d
            dist = (v0 - t0) ** 2 + (v1 - t1) ** 2

            if best_dist is None or dist < best_dist:
                best_dist = dist
                best = (v0, v1)

    return best


def add_nearby(candidates, x, max_x, window=64):
    if 0 <= x < max_x:
        for delta in range(-window, window + 1):
            y = x + delta
            if 0 <= y < max_x:
                candidates.add(int(y))


def lattice_candidates(base, prefix, multiplicity, max_x=None):
    if max_x is None:
        max_x = XBOUND

    digits = len(prefix)
    precision = digits + 90
    rf = real_field(precision, guard=80)
    modulus = ZZ(10) ** precision
    alpha_int = int(floor(rf(base).log10() * modulus))

    target_prefix = ZZ(int(prefix))
    lo = rf(target_prefix).log10() - digits + 1
    hi = rf(target_prefix + 1).log10() - digits + 1
    width = hi - lo
    width_int = max(1, int(floor(width * modulus)))
    scale = max(1, width_int // max_x)
    offset = rf(multiplicity).log10()
    candidates = set()

    targets = [lo + width * i / 8 for i in range(9)]
    for target in targets:
        target_int = int(floor(frac01(target - offset) * modulus))

        basis = Matrix(ZZ, [[modulus, 0], [alpha_int, scale]]).LLL(delta=0.99)
        close = closest_lattice_vector_2d(basis, (target_int, 0))

        for y_coord in (close[1], -close[1]):
            if y_coord % scale == 0:
                add_nearby(candidates, abs(y_coord // scale), max_x)

        basis3 = Matrix(
            ZZ,
            [
                [alpha_int, scale, 0],
                [-modulus, 0, 0],
                [-target_int, 0, max_x * scale],
            ],
        ).LLL(delta=0.99)
        rows = [[int(basis3[i, j]) for j in range(3)] for i in range(3)]

        for c0 in range(-2, 3):
            for c1 in range(-2, 3):
                for c2 in range(-2, 3):
                    if c0 == c1 == c2 == 0:
                        continue

                    row = [
                        c0 * rows[0][j] + c1 * rows[1][j] + c2 * rows[2][j]
                        for j in range(3)
                    ]

                    if row[1] % scale == 0:
                        add_nearby(candidates, abs(row[1] // scale), max_x)

    return sorted(candidates)


def find_x(nums, prefix, max_x=None):
    if max_x is None:
        max_x = XBOUND

    m = max(nums)
    multiplicity = nums.count(m)
    candidates = lattice_candidates(m, prefix, multiplicity, max_x)

    for x in candidates:
        if prefix_ok(nums, x, prefix):
            return x

    small = exact_small_x(nums, prefix)
    if small is not None:
        return small

    scanned = scan_x_logsum(nums, prefix, max_x=max_x)
    if scanned is not None:
        return scanned

    raise RuntimeError(f"x not found; tested {len(candidates)} lattice candidates")


def solve_from_values(ot_value, prefix):
    log.info("recovering nums")
    nums = recover_nums(ot_value)
    log.success(f"recovered nums; max={max(nums)} multiplicity={nums.count(max(nums))}")

    log.info("recovering x")
    x = find_x(nums, prefix)
    log.success(f"x = {x}")
    return x


def solve_interactive(io):
    io.recvuntil(b"Which number you want to know: ")
    io.sendline(str(int(QUERY_INDEX)).encode())

    io.recvuntil(b"Here is what you want: ")
    ot_value = int(io.recvline().strip())

    log.info("recovering nums")
    nums = recover_nums(ot_value)
    log.success(f"recovered nums; max={max(nums)} multiplicity={nums.count(max(nums))}")

    io.recvuntil(b"Lets play!")

    for round_index in range(16):
        io.recvuntil(f"{round_index + 1}/16".encode())
        io.recvuntil(b"challenge = ")
        prefix = io.recvline().strip().decode()
        log.info(f"round {round_index + 1}: leaked prefix = {prefix}")

        io.recvuntil(b"x = ")
        x = find_x(nums, prefix)
        log.success(f"round {round_index + 1}: x = {x}")
        io.sendline(str(x).encode())

    out = io.recvall(timeout=2)
    if out:
        print(out.decode(errors="replace").rstrip())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("host", nargs="?")
    parser.add_argument("port", nargs="?", type=int)
    parser.add_argument("--local", default=str(Path(__file__).with_name("chall.py")))
    parser.add_argument("--manual", action="store_true")
    parser.add_argument("--log-level", default="info")
    args = parser.parse_args()

    context.log_level = args.log_level

    if args.manual:
        print("Send this index:")
        print(int(QUERY_INDEX))
        ot_value = int(input("OT output: ").strip())
        prefix = input("64 leading digits: ").strip()
        print(solve_from_values(ot_value, prefix))
        return

    if (args.host is None) != (args.port is None):
        parser.error("provide both host and port, or neither for local mode")

    if args.host is not None:
        io = remote(args.host, args.port)
    else:
        local_path = Path(args.local).resolve()
        io = process([sys.executable, str(local_path)], cwd=str(local_path.parent))

    try:
        solve_interactive(io)
    finally:
        io.close()


if __name__ == "__main__":
    main()
