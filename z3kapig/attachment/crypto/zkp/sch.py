from typing import List, Tuple
import gmpy2
from crypto.zkp.hash import sha512_256i
from crypto.common.ec import ECOperations, Point
from crypto.common.numbers import rejection_sample, int_to_bytes, int_from_bytes
ProofSchBytesParts = 3


class ProofSch:

    def __init__(self, A: Point, Z: int):
        self.A = A
        self.Z = Z

    @staticmethod
    def new_proof(ssid: int, ec: ECOperations, X: Point, x: int) -> "ProofSch":
        if x is None or X is None:
            raise ValueError("Cannot generate proof from invalid input.")

        alpha, A = ProofSch.new_alpha(ec)
        return ProofSch.new_proof_with_alpha(ssid, ec, X, A, alpha, x)

    @staticmethod
    def new_alpha(ec: ECOperations) -> Tuple[int, Point]:
        alpha = ec.random_scalar()
        A = ec.scalar_mult(alpha)
        return alpha, A

    @staticmethod
    def new_proof_with_alpha(
        ssid: int, ec: ECOperations, X: Point, A: Point, alpha: int, x: int
    ) -> "ProofSch":
        if None in (x, X, A, alpha):
            raise ValueError("Cannot generate proof from invalid input.")

        q = ec.n
        g = ec.G

        e_hash = sha512_256i(
            ssid,
            ec.curve.b,
            ec.n,
            ec.p,
            X.x,
            X.y,
            g.x,
            g.y,
            A.x,
            A.y,
        )
        e = rejection_sample(q, e_hash)

        q_mpz, alpha_mpz, e_mpz, x_mpz = map(gmpy2.mpz, (q, alpha, e, x))
        z_mpz = (alpha_mpz + e_mpz * x_mpz) % q_mpz

        return ProofSch(A, int(z_mpz))

    @staticmethod
    def from_bytes(ec: ECOperations, parts: List[bytes]) -> "ProofSch":
        if not parts or len(parts) != ProofSchBytesParts:
            raise ValueError(
                f"Expected {ProofSchBytesParts} parts to construct ProofSch"
            )

        x = int_from_bytes(parts[0]) % ec.p
        y = int_from_bytes(parts[1]) % ec.p
        z = int_from_bytes(parts[2]) % ec.n

        A = Point(x, y, ec.curve)
        return ProofSch(A, z)

    def to_bytes_parts(self) -> List[bytes]:
        return [
            int_to_bytes(self.A.x),
            int_to_bytes(self.A.y),
            int_to_bytes(self.Z),
        ]

    def verify(self, ssid: int, ec: ECOperations, X: Point) -> bool:
        if self.A is None or self.Z is None or X is None:
            return False

        q = ec.n
        g = ec.G

        e_hash = sha512_256i(
            ssid,
            ec.curve.b,
            ec.n,
            ec.p,
            X.x,
            X.y,
            g.x,
            g.y,
            self.A.x,
            self.A.y,
        )
        e = rejection_sample(q, e_hash)

        left = ec.scalar_mult(self.Z)
        right = ec.point_add(self.A, ec.scalar_mult(e, X))

        return left == right
