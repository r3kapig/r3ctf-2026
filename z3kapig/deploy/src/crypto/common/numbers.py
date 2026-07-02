import secrets
import gmpy2


def jacobi_symbol(a: int, n: int) -> int:
    return gmpy2.jacobi(a, n)


def sample_invertible_with_neg_jacobi(n: int) -> int:
    while True:
        w = secrets.randbelow(int(n) - 1) + 1
        if jacobi_symbol(w, n) == -1:
            return w


def is_quadratic_residue(x: int, n: int) -> bool:
    return jacobi_symbol(x, n) == 1


def is_in_interval(x: int, bound: int) -> bool:
    return 0 <= x < bound


def check_invertible_and_valid_mod(modulus: int, *vals: int) -> bool:
    for v in vals:
        if not (0 < v < modulus):
            return False
        if gmpy2.gcd(v, modulus) != 1:
            return False
    return True


def rejection_sample(modulus: int, h: int) -> int:
    if modulus <= 0:
        raise ValueError("modulus must be positive")
    return int(h % modulus)


def random_positive_int(bound: int) -> int:
    bound = int(bound)
    if bound <= 1:
        raise ValueError("bound must be greater than 1")
    return secrets.randbelow(bound - 1) + 1


def random_nonnegative_int(bound: int) -> int:
    bound = int(bound)
    if bound <= 0:
        raise ValueError("bound must be positive")
    return secrets.randbelow(bound)


def int_to_bytes(i: int) -> bytes:
    i = int(i)
    if i == 0:
        return b""
    i = abs(i)
    return i.to_bytes((i.bit_length() + 7) // 8, "big")


def int_from_bytes(b: bytes) -> int:
    return int.from_bytes(b, "big") if b else 0
