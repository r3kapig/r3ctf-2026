from typing import List
import gmpy2
from crypto.common.ec import ECOperations, Point
from crypto.common.numbers import int_from_bytes, int_to_bytes, rejection_sample
from crypto.zkp.hash import sha512_256i

ProofSTBytesParts = 6

def second_base_point(ec: ECOperations) -> Point:
    h = rejection_sample(ec.n, sha512_256i(ec.curve.b, ec.n, ec.p, 2))
    if h == 0:
        h = 1
    return ec.scalar_mult(h)

class ProofST:
    def __init__(self, Alpha: Point, Beta: Point, T: int, U: int):
        self.Alpha = Alpha
        self.Beta = Beta
        self.T = T
        self.U = U

    @staticmethod
    def new_proof(
        ec: ECOperations,
        S: Point,
        T_commit: Point,
        R: Point,
        H: Point,
        sigma: int,
        blind: int,
    ) -> "ProofST":
        if any(v is None for v in [ec, S, T_commit, R, H, sigma, blind]):
            raise ValueError("ProofST.new_proof received nil input")

        q = gmpy2.mpz(ec.n)
        a = gmpy2.mpz(ec.random_scalar())
        b = gmpy2.mpz(ec.random_scalar())

        alpha = ec.scalar_mult(int(a), R)
        beta = ec.point_add(ec.scalar_mult(int(a)), ec.scalar_mult(int(b), H))

        c = ProofST._challenge(ec, T_commit, H, alpha, beta)
        t = (a + gmpy2.mpz(c) * gmpy2.mpz(sigma)) % q
        u = (b + gmpy2.mpz(c) * gmpy2.mpz(blind)) % q
        return ProofST(alpha, beta, int(t), int(u))

    @staticmethod
    def _challenge(
        ec: ECOperations, T_commit: Point, H: Point, Alpha: Point, Beta: Point
    ) -> int:
        g = ec.G
        h = sha512_256i(
            T_commit.x,
            T_commit.y,
            H.x,
            H.y,
            g.x,
            g.y,
            Alpha.x,
            Alpha.y,
            Beta.x,
            Beta.y,
        )
        return rejection_sample(ec.n, h)

    @staticmethod
    def from_bytes(ec: ECOperations, parts: List[bytes]) -> "ProofST":
        if not parts or len(parts) != ProofSTBytesParts:
            raise ValueError(f"expected {ProofSTBytesParts} parts to construct ProofST")
        alpha = Point(int_from_bytes(parts[0]), int_from_bytes(parts[1]), ec.curve)
        beta = Point(int_from_bytes(parts[2]), int_from_bytes(parts[3]), ec.curve)
        return ProofST(alpha, beta, int_from_bytes(parts[4]), int_from_bytes(parts[5]))

    def to_bytes_parts(self) -> List[bytes]:
        return [
            int_to_bytes(self.Alpha.x),
            int_to_bytes(self.Alpha.y),
            int_to_bytes(self.Beta.x),
            int_to_bytes(self.Beta.y),
            int_to_bytes(self.T),
            int_to_bytes(self.U),
        ]

    def validate_basic(self) -> bool:
        return all(v is not None for v in [self.Alpha, self.Beta, self.T, self.U])

    def verify(
        self, ec: ECOperations, S: Point, T_commit: Point, R: Point, H: Point
    ) -> bool:
        if not self.validate_basic() or any(
            v is None for v in [ec, S, T_commit, R, H]
        ):
            return False

        c = self._challenge(ec, T_commit, H, self.Alpha, self.Beta)

        left1 = ec.scalar_mult(self.T, R)
        right1 = ec.point_add(self.Alpha, ec.scalar_mult(c, S))
        if left1 != right1:
            return False

        left2 = ec.point_add(ec.scalar_mult(self.T), ec.scalar_mult(self.U, H))
        right2 = ec.point_add(self.Beta, ec.scalar_mult(c, T_commit))
        return left2 == right2
