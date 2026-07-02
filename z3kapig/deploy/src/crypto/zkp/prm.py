from typing import List
import gmpy2
from crypto.zkp.hash import sha512_256i
from crypto.common.numbers import random_nonnegative_int, int_to_bytes, int_from_bytes

Iterations = 80
ProofPrmBytesParts = Iterations * 2

class ProofPrm:

    def __init__(self, A: List[int], Z: List[int]):
        self.A = A
        self.Z = Z

    @staticmethod
    def new_proof(ssid: int, s: int, t: int, N: int, Phi: int, lam: int) -> "ProofPrm":
        if not all([s, t, N, Phi, lam]):
            raise ValueError("Prm proof input is not valid")

        s, t, N, Phi, lam = map(gmpy2.mpz, (s, t, N, Phi, lam))
        a = [gmpy2.mpz(random_nonnegative_int(Phi)) for _ in range(Iterations)]
        A = [gmpy2.powmod(t, ai, N) for ai in a]
        e = sha512_256i(*([ssid, int(s), int(t), int(N)] + [int(val) for val in A]))
        Z = [(a[i] + (((e >> i) & 1) * lam)) % Phi for i in range(Iterations)]

        return ProofPrm([int(val) for val in A], [int(val) for val in Z])

    @staticmethod
    def from_bytes(parts: List[bytes]) -> "ProofPrm":
        if not parts or len(parts) != ProofPrmBytesParts:
            raise ValueError(
                f"expected {ProofPrmBytesParts} byte parts to construct ProofPrm"
            )
        bis = [int_from_bytes(b) for b in parts]
        A = bis[:Iterations]
        Z = bis[Iterations:]
        return ProofPrm(A, Z)

    def to_bytes_parts(self) -> List[bytes]:

        out: List[bytes] = []
        out += [int_to_bytes(a) for a in self.A]
        out += [int_to_bytes(z) for z in self.Z]
        return out

    def validate_basic(self) -> bool:
        if self.A is None or any(a is None for a in self.A):
            return False
        if self.Z is None or any(z is None for z in self.Z):
            return False
        return True

    def verify(self, ssid: int, s: int, t: int, N: int) -> bool:
        if not self.validate_basic() or not all([s, t, N]) or N <= 0:
            return False

        s_mpz, t_mpz, N_mpz = map(gmpy2.mpz, (s, t, N))
        A_mpz = [gmpy2.mpz(a) for a in self.A]
        Z_mpz = [gmpy2.mpz(z) for z in self.Z]

        e = sha512_256i(*([ssid, s, t, N] + self.A))

        s_, t_ = s_mpz % N_mpz, t_mpz % N_mpz
        if not (1 < s_ < N_mpz) or not (1 < t_ < N_mpz) or s_ == t_:
            return False
        for a in A_mpz:
            if not (1 < a < N_mpz):
                return False
        for z in Z_mpz:
            if z < 0:
                return False

        for i in range(Iterations):
            ei = (e >> i) & 1

            left = gmpy2.powmod(t_mpz, Z_mpz[i], N_mpz)
            right_term = gmpy2.powmod(s_mpz, ei, N_mpz)
            right = (A_mpz[i] * right_term) % N_mpz

            if left != right:
                return False

        return True
