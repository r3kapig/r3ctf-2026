
from typing import List
import gmpy2

from crypto.zkp.hash import sha512_256i
from crypto.common.ec import ECOperations
from crypto.common.numbers import (
    rejection_sample,
    check_invertible_and_valid_mod,
    is_in_interval,
    random_nonnegative_int,
    int_to_bytes,
    int_from_bytes,
)


ProofFacBytesParts = 11


class ProofFac:

    def __init__(
        self,
        P: int,
        Q: int,
        A: int,
        B: int,
        T: int,
        Sigma: int,
        Z1: int,
        Z2: int,
        W1: int,
        W2: int,
        V: int,
    ) -> None:
        self.P = P
        self.Q = Q
        self.A = A
        self.B = B
        self.T = T
        self.Sigma = Sigma
        self.Z1 = Z1
        self.Z2 = Z2
        self.W1 = W1
        self.W2 = W2
        self.V = V

    @staticmethod
    def new_proof(
        ssid: int,
        ec: ECOperations,
        N0: int,
        NCap: int,
        s: int,
        t: int,
        N0p: int,
        N0q: int,
    ) -> "ProofFac":
        if not all([N0, NCap, s, t, N0p, N0q]):
            raise ValueError("new_proof received a nil/zero argument")

        q, q3 = gmpy2.mpz(ec.n), gmpy2.mpz(ec.n) ** 3
        N0, NCap = map(gmpy2.mpz, (N0, NCap))
        s, t, N0p, N0q = map(gmpy2.mpz, (s, t, N0p, N0q))

        sqrtN0 = gmpy2.isqrt(N0)
        leSqrtN0 = q3 * sqrtN0
        lNCap = q * NCap
        lN0NCap = q * N0 * NCap
        leN0NCap = q3 * N0 * NCap
        leNCap = q3 * NCap

        alpha = gmpy2.mpz(random_nonnegative_int(leSqrtN0))
        beta = gmpy2.mpz(random_nonnegative_int(leSqrtN0))
        mu = gmpy2.mpz(random_nonnegative_int(lNCap))
        nu = gmpy2.mpz(random_nonnegative_int(lNCap))
        sigma = gmpy2.mpz(random_nonnegative_int(lN0NCap))
        x = gmpy2.mpz(random_nonnegative_int(leNCap))
        y = gmpy2.mpz(random_nonnegative_int(leNCap))
        r = gmpy2.mpz(random_nonnegative_int(leN0NCap))

        P = (gmpy2.powmod(s, N0p, NCap) * gmpy2.powmod(t, mu, NCap)) % NCap
        Q = (gmpy2.powmod(s, N0q, NCap) * gmpy2.powmod(t, nu, NCap)) % NCap
        A = (gmpy2.powmod(s, alpha, NCap) * gmpy2.powmod(t, x, NCap)) % NCap
        B = (gmpy2.powmod(s, beta, NCap) * gmpy2.powmod(t, y, NCap)) % NCap
        T = (gmpy2.powmod(Q, alpha, NCap) * gmpy2.powmod(t, r, NCap)) % NCap

        e_hash = sha512_256i(
            ssid,
            N0,
            NCap,
            s,
            t,
            P,
            Q,
            A,
            B,
            T,
            sigma,
            ec.curve.b,
            ec.n,
            ec.p,
        )
        e = gmpy2.mpz(rejection_sample(int(q), e_hash))

        z1 = e * N0p + alpha
        z2 = e * N0q + beta
        w1 = e * mu + x
        w2 = e * nu + y
        v = e * (sigma - (nu * N0p)) + r

        return ProofFac(
            int(P),
            int(Q),
            int(A),
            int(B),
            int(T),
            int(sigma),
            int(z1),
            int(z2),
            int(w1),
            int(w2),
            int(v),
        )

    @staticmethod
    def from_bytes(parts: List[bytes]) -> "ProofFac":
        if not parts or len(parts) != ProofFacBytesParts:
            raise ValueError(
                f"expected {ProofFacBytesParts} byte parts to construct ProofFac"
            )

        return ProofFac(
            int_from_bytes(parts[0]),
            int_from_bytes(parts[1]),
            int_from_bytes(parts[2]),
            int_from_bytes(parts[3]),
            int_from_bytes(parts[4]),
            int_from_bytes(parts[5]),
            int_from_bytes(parts[6]),
            int_from_bytes(parts[7]),
            int_from_bytes(parts[8]),
            int_from_bytes(parts[9]),
            int_from_bytes(parts[10]),
        )

    def to_bytes_parts(self) -> List[bytes]:

        return [
            int_to_bytes(self.P),
            int_to_bytes(self.Q),
            int_to_bytes(self.A),
            int_to_bytes(self.B),
            int_to_bytes(self.T),
            int_to_bytes(self.Sigma),
            int_to_bytes(self.Z1),
            int_to_bytes(self.Z2),
            int_to_bytes(self.W1),
            int_to_bytes(self.W2),
            int_to_bytes(self.V),
        ]

    def validate_basic(self) -> bool:
        return all(
            [
                self.P is not None,
                self.Q is not None,
                self.A is not None,
                self.B is not None,
                self.T is not None,
                self.Sigma is not None,
                self.Z1 is not None,
                self.Z2 is not None,
                self.W1 is not None,
                self.W2 is not None,
                self.V is not None,
            ]
        )

    def verify(
        self, ssid: int, ec: ECOperations, N0: int, NCap: int, s: int, t: int
    ) -> bool:
        if not self.validate_basic() or not all([N0, NCap, s, t]):
            return False
        if N0 <= 0 or NCap <= 0:
            return False

        q, q3 = gmpy2.mpz(ec.n), gmpy2.mpz(ec.n) ** 3
        N0, NCap, s, t = map(gmpy2.mpz, (N0, NCap, s, t))
        P, Q, A, B, T = map(gmpy2.mpz, (self.P, self.Q, self.A, self.B, self.T))
        Sigma, Z1, Z2 = map(gmpy2.mpz, (self.Sigma, self.Z1, self.Z2))
        W1, W2, V = map(gmpy2.mpz, (self.W1, self.W2, self.V))

        sqrtN0 = gmpy2.isqrt(N0)
        leSqrtN0 = q3 * sqrtN0

        if not is_in_interval(Z1, leSqrtN0):
            return False
        if not is_in_interval(Z2, leSqrtN0):
            return False
        if not check_invertible_and_valid_mod(NCap, P, Q, A, B, T):
            return False

        e_hash = sha512_256i(
            ssid,
            N0,
            NCap,
            s,
            t,
            self.P,
            self.Q,
            self.A,
            self.B,
            self.T,
            self.Sigma,
            ec.curve.b,
            ec.n,
            ec.p,
        )
        e = gmpy2.mpz(rejection_sample(int(q), e_hash))

        LHS1 = (gmpy2.powmod(s, Z1, NCap) * gmpy2.powmod(t, W1, NCap)) % NCap
        RHS1 = (A * gmpy2.powmod(P, e, NCap)) % NCap
        if LHS1 != RHS1:
            return False

        LHS2 = (gmpy2.powmod(s, Z2, NCap) * gmpy2.powmod(t, W2, NCap)) % NCap
        RHS2 = (B * gmpy2.powmod(Q, e, NCap)) % NCap
        if LHS2 != RHS2:
            return False

        R = (gmpy2.powmod(s, N0, NCap) * gmpy2.powmod(t, Sigma, NCap)) % NCap
        LHS3 = (gmpy2.powmod(Q, Z1, NCap) * gmpy2.powmod(t, V, NCap)) % NCap
        RHS3 = (T * gmpy2.powmod(R, e, NCap)) % NCap
        if LHS3 != RHS3:
            return False
        return True
