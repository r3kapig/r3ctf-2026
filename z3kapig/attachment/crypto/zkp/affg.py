from typing import List
import gmpy2
from crypto.zkp.hash import sha512_256i
from crypto.common.paillier import PublicKey
from crypto.common.paillier import get_random_positive_relatively_prime_int
from crypto.common.ec import ECOperations, Point
from crypto.common.numbers import (
    rejection_sample,
    check_invertible_and_valid_mod,
    is_in_interval,
    random_nonnegative_int,
    int_to_bytes,
    int_from_bytes,
)

ProofAffgBytesParts = 14


class ProofAffg:

    def __init__(
        self,
        S: int,
        T: int,
        A: int,
        Bx: Point,
        By: int,
        E: int,
        F: int,
        Z1: int,
        Z2: int,
        Z3: int,
        Z4: int,
        W: int,
        Wy: int,
    ) -> None:
        self.S = S
        self.T = T
        self.A = A
        self.Bx = Bx
        self.By = By
        self.E = E
        self.F = F
        self.Z1 = Z1
        self.Z2 = Z2
        self.Z3 = Z3
        self.Z4 = Z4
        self.W = W
        self.Wy = Wy

    @staticmethod
    def new_proof(
        ssid: int,
        ec: ECOperations,
        pk0: PublicKey,
        pk1: PublicKey,
        NCap: int,
        s: int,
        t: int,
        C: int,
        D: int,
        Y: int,
        X: Point,
        x: int,
        y: int,
        rho: int,
        rhoy: int,
    ) -> "ProofAffg":
        if not all([ec, pk0, pk1, NCap, s, t, C, D, Y, X, x, y, rho, rhoy]):
            raise ValueError("new_proof() received a nil/zero argument")

        q = gmpy2.mpz(ec.n)
        N0, NSq0, gamma0 = map(gmpy2.mpz, (pk0.n, pk0.n_square, pk0.gamma))
        N1, NSq1, gamma1 = map(gmpy2.mpz, (pk1.n, pk1.n_square, pk1.gamma))
        NCap, s, t = map(gmpy2.mpz, (NCap, s, t))
        C, D, Y = map(gmpy2.mpz, (C, D, Y))
        x, y, rho, rhoy = map(gmpy2.mpz, (x, y, rho, rhoy))

        q3 = q**3
        qNCap = q * NCap
        q3NCap = q3 * NCap


        alpha = gmpy2.mpz(random_nonnegative_int(q3))
        beta = gmpy2.mpz(get_random_positive_relatively_prime_int(pk0.n))
        r = gmpy2.mpz(get_random_positive_relatively_prime_int(pk0.n))
        ry = gmpy2.mpz(get_random_positive_relatively_prime_int(pk1.n))
        gamma = gmpy2.mpz(random_nonnegative_int(q3NCap))
        m = gmpy2.mpz(random_nonnegative_int(qNCap))
        delta = gmpy2.mpz(random_nonnegative_int(q3NCap))
        mu = gmpy2.mpz(random_nonnegative_int(qNCap))

        A_term1 = gmpy2.powmod(C, alpha, NSq0)
        A_term2 = gmpy2.powmod(gamma0, beta, NSq0)
        A_term3 = gmpy2.powmod(r, N0, NSq0)
        A = (A_term1 * A_term2 * A_term3) % NSq0

        Bx = ec.scalar_mult(int(alpha % q))                
        By = (gmpy2.powmod(gamma1, beta, NSq1) * gmpy2.powmod(ry, N1, NSq1)) % NSq1

        E = (gmpy2.powmod(s, alpha, NCap) * gmpy2.powmod(t, gamma, NCap)) % NCap
        S = (gmpy2.powmod(s, x, NCap) * gmpy2.powmod(t, m, NCap)) % NCap
        F = (gmpy2.powmod(s, beta, NCap) * gmpy2.powmod(t, delta, NCap)) % NCap
        T = (gmpy2.powmod(s, y, NCap) * gmpy2.powmod(t, mu, NCap)) % NCap

        e_hash = sha512_256i(
            ssid,
            ec.curve.b,
            ec.n,
            ec.p,
            pk0.n,
            pk1.n,
            NCap,
            s,
            t,
            C,
            D,
            Y,
            X.x,
            X.y,
            S,
            T,
            A,
            Bx.x,
            Bx.y,
            By,
            E,
            F,
        )
        e = gmpy2.mpz(rejection_sample(int(q), e_hash))

        z1 = e * x + alpha
        z2 = e * y + beta
        z3 = e * m + gamma
        z4 = e * mu + delta
        w = (gmpy2.powmod(rho, e, N0) * r) % N0
        wy = (gmpy2.powmod(rhoy, e, N1) * ry) % N1

        return ProofAffg(
            int(S),
            int(T),
            int(A),
            Bx,
            int(By),
            int(E),
            int(F),
            int(z1),
            int(z2),
            int(z3),
            int(z4),
            int(w),
            int(wy),
        )

    @staticmethod
    def from_bytes(ec: ECOperations, parts: List[bytes]) -> "ProofAffg":
        if not parts or len(parts) != ProofAffgBytesParts:
            raise ValueError(
                f"expected {ProofAffgBytesParts} parts to construct ProofAffg"
            )

        Bx = Point(int_from_bytes(parts[3]), int_from_bytes(parts[4]), ec.curve)
        return ProofAffg(
            int_from_bytes(parts[0]),
            int_from_bytes(parts[1]),
            int_from_bytes(parts[2]),
            Bx,
            int_from_bytes(parts[5]),
            int_from_bytes(parts[6]),
            int_from_bytes(parts[7]),
            int_from_bytes(parts[8]),
            int_from_bytes(parts[9]),
            int_from_bytes(parts[10]),
            int_from_bytes(parts[11]),
            int_from_bytes(parts[12]),
            int_from_bytes(parts[13]),
        )

    def to_bytes_parts(self) -> List[bytes]:

        return [
            int_to_bytes(self.S),
            int_to_bytes(self.T),
            int_to_bytes(self.A),
            int_to_bytes(self.Bx.x),
            int_to_bytes(self.Bx.y),
            int_to_bytes(self.By),
            int_to_bytes(self.E),
            int_to_bytes(self.F),
            int_to_bytes(self.Z1),
            int_to_bytes(self.Z2),
            int_to_bytes(self.Z3),
            int_to_bytes(self.Z4),
            int_to_bytes(self.W),
            int_to_bytes(self.Wy),
        ]

    def validate_basic(self) -> bool:
        return all(
            [
                self.S is not None,
                self.T is not None,
                self.A is not None,
                self.Bx is not None,
                self.By is not None,
                self.E is not None,
                self.F is not None,
                self.Z1 is not None,
                self.Z2 is not None,
                self.Z3 is not None,
                self.Z4 is not None,
                self.W is not None,
                self.Wy is not None,
            ]
        )

    def verify(
        self,
        ssid: int,
        ec: ECOperations,
        pk0: PublicKey,
        pk1: PublicKey,
        NCap: int,
        s: int,
        t: int,
        C: int,
        D: int,
        Y: int,
        X: Point,
    ) -> bool:
        if not self.validate_basic():
            return False

        q = gmpy2.mpz(ec.n)
        N0, NSq0, gamma0 = map(gmpy2.mpz, (pk0.n, pk0.n_square, pk0.gamma))
        N1, NSq1, gamma1 = map(gmpy2.mpz, (pk1.n, pk1.n_square, pk1.gamma))
        NCap, s, t = map(gmpy2.mpz, (NCap, s, t))
        C, D, Y = map(gmpy2.mpz, (C, D, Y))

        S, T, A, By = map(gmpy2.mpz, (self.S, self.T, self.A, self.By))
        E, F, W, Wy = map(gmpy2.mpz, (self.E, self.F, self.W, self.Wy))
        Z1, Z2, Z3, Z4 = map(gmpy2.mpz, (self.Z1, self.Z2, self.Z3, self.Z4))

        q3 = q**3


        if not is_in_interval(Z1, q3):
            return False
        if not check_invertible_and_valid_mod(NSq0, A):
            return False
        if not check_invertible_and_valid_mod(NSq1, By):
            return False
        if not check_invertible_and_valid_mod(N0, W):
            return False
        if not check_invertible_and_valid_mod(N1, Wy):
            return False
        if not check_invertible_and_valid_mod(NCap, E, F, S, T):
            return False
        if min(Z1, Z2, Z3, Z4) <= 0:
            return False

        e_hash = sha512_256i(
            ssid,
            ec.curve.b,
            ec.n,
            ec.p,
            pk0.n,
            pk1.n,
            NCap,
            s,
            t,
            C,
            D,
            Y,
            X.x,
            X.y,
            self.S,
            self.T,
            self.A,
            self.Bx.x,
            self.Bx.y,
            self.By,
            self.E,
            self.F,
        )
        e = gmpy2.mpz(rejection_sample(int(q), e_hash))

        left1 = gmpy2.powmod(C, Z1, NSq0)
        left1 = (left1 * gmpy2.powmod(gamma0, Z2, NSq0)) % NSq0
        left1 = (left1 * gmpy2.powmod(W, N0, NSq0)) % NSq0
        right1 = (gmpy2.powmod(D, e, NSq0) * A) % NSq0
        if left1 != right1:
            return False

        g_exp_z1 = ec.scalar_mult(int(Z1 % q))
        x_exp_e = ec.scalar_mult(int(e), X)
        bx_sum = ec.point_add(x_exp_e, self.Bx)
        if g_exp_z1 != bx_sum:
            return False

        left3 = (gmpy2.powmod(gamma1, Z2, NSq1) * gmpy2.powmod(Wy, N1, NSq1)) % NSq1
        right3 = (gmpy2.powmod(Y, e, NSq1) * By) % NSq1
        if left3 != right3:
            return False

        left4a = (gmpy2.powmod(s, Z1, NCap) * gmpy2.powmod(t, Z3, NCap)) % NCap
        right4a = (gmpy2.powmod(S, e, NCap) * E) % NCap
        if left4a != right4a:
            return False

        left4b = (gmpy2.powmod(s, Z2, NCap) * gmpy2.powmod(t, Z4, NCap)) % NCap
        right4b = (gmpy2.powmod(T, e, NCap) * F) % NCap
        if left4b != right4b:
            return False

        return True
