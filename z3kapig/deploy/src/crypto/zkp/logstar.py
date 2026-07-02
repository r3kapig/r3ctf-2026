from typing import List
import gmpy2
from crypto.zkp.hash import sha512_256i
from crypto.common.paillier import PublicKey
from crypto.common.ec import ECOperations, Point
from crypto.common.numbers import (
    rejection_sample,
    check_invertible_and_valid_mod,
    is_in_interval,
    random_nonnegative_int,
    random_positive_int,
    int_to_bytes,
    int_from_bytes,
)

ProofLogstarBytesParts = 8


class ProofLogstar:

    def __init__(self, S: int, A: int, Y: Point, D: int, Z1: int, Z2: int, Z3: int):
        self.S = S
        self.A = A
        self.Y = Y
        self.D = D
        self.Z1 = Z1
        self.Z2 = Z2
        self.Z3 = Z3

    @staticmethod
    def new_proof(
        ssid: int,
        ec: ECOperations,
        pk: PublicKey,
        C: int,
        X: Point,
        g: Point,
        rho: int,
        x: int,
        NCap: int,
        s: int,
        t: int,
    ) -> "ProofLogstar":
        if any(c is None for c in [ec, pk, C, X, g, NCap, s, t, x, rho]):
            raise ValueError("new_proof received a nil/zero argument")

        q = gmpy2.mpz(ec.n)
        N, NSq, gamma_pk = map(gmpy2.mpz, (pk.n, pk.n_square, pk.gamma))
        C, x, rho = map(gmpy2.mpz, (C, x, rho))
        NCap, s, t = map(gmpy2.mpz, (NCap, s, t))

        q3 = q**3
        qNCap = q * NCap
        q3NCap = q3 * NCap

        alpha = gmpy2.mpz(random_nonnegative_int(q3))
        mu = gmpy2.mpz(random_nonnegative_int(qNCap))
        gamma = gmpy2.mpz(random_nonnegative_int(q3NCap))
        r = gmpy2.mpz(random_positive_int(N))
        while gmpy2.gcd(r, N) != 1:
            r = gmpy2.mpz(random_positive_int(N))

        S = (gmpy2.powmod(s, x, NCap) * gmpy2.powmod(t, mu, NCap)) % NCap
        A = (gmpy2.powmod(gamma_pk, alpha, NSq) * gmpy2.powmod(r, N, NSq)) % NSq
        Y = ec.scalar_mult(int(alpha % q), g)
        D = (gmpy2.powmod(s, alpha, NCap) * gmpy2.powmod(t, gamma, NCap)) % NCap

        e_hash = sha512_256i(
            ssid,
            pk.n,
            pk.gamma,
            ec.curve.b,
            ec.n,
            ec.p,
            C,
            X.x,
            X.y,
            g.x,
            g.y,
            S,
            A,
            Y.x,
            Y.y,
            D,
            NCap,
            s,
            t,
        )
        e = gmpy2.mpz(rejection_sample(int(q), e_hash))

        z1 = e * x + alpha
        z2 = (gmpy2.powmod(rho, e, N) * r) % N
        z3 = e * mu + gamma

        return ProofLogstar(int(S), int(A), Y, int(D), int(z1), int(z2), int(z3))

    @staticmethod
    def from_bytes(ec: ECOperations, parts: List[bytes]) -> "ProofLogstar":
        if not parts or len(parts) != ProofLogstarBytesParts:
            raise ValueError(f"expected {ProofLogstarBytesParts} byte parts")

        Y = Point(int_from_bytes(parts[2]), int_from_bytes(parts[3]), ec.curve)
        return ProofLogstar(
            int_from_bytes(parts[0]),
            int_from_bytes(parts[1]),
            Y,
            int_from_bytes(parts[4]),
            int_from_bytes(parts[5]),
            int_from_bytes(parts[6]),
            int_from_bytes(parts[7]),
        )

    def to_bytes_parts(self) -> List[bytes]:

        return [
            int_to_bytes(self.S),
            int_to_bytes(self.A),
            int_to_bytes(self.Y.x),
            int_to_bytes(self.Y.y),
            int_to_bytes(self.D),
            int_to_bytes(self.Z1),
            int_to_bytes(self.Z2),
            int_to_bytes(self.Z3),
        ]

    def validate_basic(self) -> bool:
        return all(
            p is not None
            for p in [self.S, self.A, self.Y, self.D, self.Z1, self.Z2, self.Z3]
        )

    def verify(
        self,
        ssid: int,
        ec: ECOperations,
        pk: PublicKey,
        C: int,
        X: Point,
        g: Point,
        NCap: int,
        s: int,
        t: int,
    ) -> bool:
        if not self.validate_basic() or not all([ec, pk, C, X, g, NCap, s, t]):
            return False

        q = gmpy2.mpz(ec.n)
        N, NSq, gamma_pk = map(gmpy2.mpz, (pk.n, pk.n_square, pk.gamma))
        C, NCap, s, t = map(gmpy2.mpz, (C, NCap, s, t))
        S, A, D, Z1, Z2, Z3 = map(
            gmpy2.mpz, (self.S, self.A, self.D, self.Z1, self.Z2, self.Z3)
        )

        q3 = q**3
        if not is_in_interval(Z1, q3):
            return False
        if not check_invertible_and_valid_mod(NCap, S, D):
            return False
        if not check_invertible_and_valid_mod(NSq, A):
            return False
        if not check_invertible_and_valid_mod(N, Z2):
            return False

        e_hash = sha512_256i(
            ssid,
            pk.n,
            pk.gamma,
            ec.curve.b,
            ec.n,
            ec.p,
            C,
            X.x,
            X.y,
            g.x,
            g.y,
            self.S,
            self.A,
            self.Y.x,
            self.Y.y,
            self.D,
            NCap,
            s,
            t,
        )
        e = gmpy2.mpz(rejection_sample(int(q), e_hash))

        left1 = (gmpy2.powmod(gamma_pk, Z1, NSq) * gmpy2.powmod(Z2, N, NSq)) % NSq
        right1 = (gmpy2.powmod(C, e, NSq) * A) % NSq
        if left1 != right1:
            return False

        left2 = ec.scalar_mult(int(Z1 % q), g)
        right2 = ec.point_add(ec.scalar_mult(int(e), X), self.Y)
        if left2 != right2:
            return False

        left3 = (gmpy2.powmod(s, Z1, NCap) * gmpy2.powmod(t, Z3, NCap)) % NCap
        right3 = (D * gmpy2.powmod(S, e, NCap)) % NCap
        if left3 != right3:
            return False

        return True
