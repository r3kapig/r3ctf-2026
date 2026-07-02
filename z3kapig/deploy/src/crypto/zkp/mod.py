from typing import List
import gmpy2
from crypto.zkp.hash import sha512_256i
from crypto.common.numbers import (
    sample_invertible_with_neg_jacobi,
    is_quadratic_residue,
    rejection_sample,
    int_to_bytes,
    int_from_bytes,
)

Iterations = 80
ProofModBytesParts = Iterations * 2 + 3

class ProofMod:

    def __init__(self, W: int, X: List[int], A: int, B: int, Z: List[int]):
        self.W = W
        self.X = X
        self.A = A
        self.B = B
        self.Z = Z

    @staticmethod
    def new_proof(ssid: int, N: int, P: int, Q: int) -> "ProofMod":
        if not all([N, P, Q]):
            raise ValueError("Proof mod input is not valid")

        N, P, Q = map(gmpy2.mpz, (N, P, Q))
        Phi = (P - 1) * (Q - 1)


        W = gmpy2.mpz(sample_invertible_with_neg_jacobi(N))


        Y: List[int] = [0] * Iterations
        for i in range(Iterations):
            prefix = [ssid, W, N] + Y[:i]
            ei = sha512_256i(*prefix)
            Y[i] = rejection_sample(N, ei)

        Y_mpz = [gmpy2.mpz(y) for y in Y]

        try:
            invN = gmpy2.invert(N, Phi)
        except ZeroDivisionError:                                              
            raise ValueError("N is not invertible modulo Phi")

        X: List[gmpy2.mpz] = [gmpy2.mpz(0)] * Iterations
        Z: List[gmpy2.mpz] = [gmpy2.mpz(0)] * Iterations

        A = gmpy2.mpz(0xFF)
        B = gmpy2.mpz(0xFF)

        expo = gmpy2.powmod((Phi + 4) >> 3, 2, Phi)

        for i in range(Iterations):

            for j in range(4):
                a = j & 1
                b = (j & 2) >> 1
                Yi = Y_mpz[i]
                if a > 0:
                    Yi = -Yi % N
                if b > 0:
                    Yi = (W * Yi) % N

                if is_quadratic_residue(Yi, P) and is_quadratic_residue(Yi, Q):
                    X[i] = gmpy2.powmod(Yi, expo, N)
                    Z[i] = gmpy2.powmod(Y_mpz[i], invN, N)

                    A = (A << 8) | a
                    B = (B << 8) | b
                    break

        return ProofMod(
            int(W), [int(x) for x in X], int(A), int(B), [int(z) for z in Z]
        )

    @staticmethod
    def from_bytes(parts: List[bytes]) -> "ProofMod":
        if not parts or len(parts) != ProofModBytesParts:
            raise ValueError(
                f"expected {ProofModBytesParts} byte parts to construct ProofMod"
            )

        ints = [int_from_bytes(b) for b in parts]
        W = ints[0]
        X = ints[1 : Iterations + 1]
        A = ints[Iterations + 1]
        B = ints[Iterations + 2]
        Z = ints[Iterations + 3 :]
        return ProofMod(W, X, A, B, Z)

    def to_bytes_parts(self) -> List[bytes]:

        out: List[bytes] = [int_to_bytes(self.W)]
        out += [int_to_bytes(x) for x in self.X]
        out.append(int_to_bytes(self.A))
        out.append(int_to_bytes(self.B))
        out += [int_to_bytes(z) for z in self.Z]
        return out

    def validate_basic(self) -> bool:
        return all(
            [
                self.W is not None,
                self.X is not None and not any(x is None for x in self.X),
                self.A is not None,
                self.B is not None,
                self.Z is not None and not any(z is None for z in self.Z),
            ]
        )

    def verify(self, ssid: int, N: int) -> bool:
        if not self.validate_basic() or not N:
            return False

        N = gmpy2.mpz(N)
        W, A, B = map(gmpy2.mpz, (self.W, self.A, self.B))
        X = [gmpy2.mpz(x) for x in self.X]
        Z = [gmpy2.mpz(z) for z in self.Z]

        if is_quadratic_residue(W, N) == 1:
            return False
        if not (0 < W < N and all(0 < z < N for z in Z) and all(0 < x < N for x in X)):
            return False

        expected_len_in_bits = 8 * (Iterations + 1)
        if not (expected_len_in_bits - 8 < A.bit_length() <= expected_len_in_bits):
            return False
        if not (expected_len_in_bits - 8 < B.bit_length() <= expected_len_in_bits):
            return False

        Y: List[gmpy2.mpz] = [gmpy2.mpz(0)] * Iterations
        for i in range(Iterations):
            prefix = [ssid, W, N] + [int(y) for y in Y[:i]]
            ei = sha512_256i(*prefix)
            Y[i] = gmpy2.mpz(rejection_sample(N, ei))

        if not gmpy2.is_odd(N):
            return False

        for i in range(Iterations):

            if gmpy2.powmod(Z[i], N, N) != Y[i]:
                return False

            shift = 8 * (Iterations - 1 - i)
            a = (A >> shift) & 0xFF
            b = (B >> shift) & 0xFF

            if a not in (0, 1) or b not in (0, 1):
                return False

            left = gmpy2.powmod(X[i], 4, N)
            right = Y[i]
            if a > 0:
                right = -right % N
            if b > 0:
                right = (W * right) % N

            if left != right:
                return False

        return True
