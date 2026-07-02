from typing import Tuple, Optional, Union
import secrets
import gmpy2

class Secp256k1:

    def __init__(self):

        self.p: gmpy2.mpz = gmpy2.mpz(
            "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F", 16
        )
        self.a: gmpy2.mpz = gmpy2.mpz(0)
        self.b: gmpy2.mpz = gmpy2.mpz(7)

        self.n: gmpy2.mpz = gmpy2.mpz(
            "FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141", 16
        )

        gx: gmpy2.mpz = gmpy2.mpz(
            "79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798", 16
        )
        gy: gmpy2.mpz = gmpy2.mpz(
            "483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8", 16
        )
        self.G: "Point" = Point(gx, gy, self)

    def is_on_curve(self, x: gmpy2.mpz, y: gmpy2.mpz) -> bool:
        left = gmpy2.powmod(y, 2, self.p)
        right = (gmpy2.powmod(x, 3, self.p) + self.b) % self.p
        return left == right


class Point:

    def __init__(
        self, x: Optional[gmpy2.mpz], y: Optional[gmpy2.mpz], curve: Secp256k1
    ):
        self.x = x
        self.y = y
        self.curve = curve
        self.is_infinity = (x is None and y is None) or (x == 0 and y == 0)

        if not self.is_infinity and not curve.is_on_curve(x, y):
            raise ValueError(f"Point ({hex(x)}, {hex(y)}) is not on the curve")

    def __eq__(self, other: "Point") -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        if self.is_infinity and other.is_infinity:
            return True
        if self.is_infinity or other.is_infinity:
            return False
        return self.x == other.x and self.y == other.y

    def __repr__(self) -> str:
        if self.is_infinity:
            return "Point(INF)"
        return f"Point({hex(self.x)}, {hex(self.y)})"

    @staticmethod
    def infinity(curve: Secp256k1) -> "Point":
        return Point(0, 0, curve)


class ECOperations:

    def __init__(self):
        self.curve = Secp256k1()
        self.G = self.curve.G
        self.n = self.curve.n
        self.p = self.curve.p

    def random_scalar(self) -> int:
        return secrets.randbelow(int(self.n) - 1) + 1

    def point_add(self, p1: Point, p2: Point) -> Point:
        if p1.is_infinity:
            return p2
        if p2.is_infinity:
            return p1
        if p1.x == p2.x:
            return self.point_double(p1) if p1.y == p2.y else Point.infinity(self.curve)

        dx = p2.x - p1.x
        dy = p2.y - p1.y
        slope = (dy * gmpy2.invert(dx, self.p)) % self.p

        x3 = (gmpy2.powmod(slope, 2, self.p) - p1.x - p2.x) % self.p
        y3 = (slope * (p1.x - x3) - p1.y) % self.p

        return Point(x3, y3, self.curve)

    def point_double(self, p: Point) -> Point:
        if p.is_infinity or p.y == 0:
            return Point.infinity(self.curve)

        numerator = 3 * gmpy2.powmod(p.x, 2, self.p)
        denominator = 2 * p.y
        slope = (numerator * gmpy2.invert(denominator, self.p)) % self.p

        x3 = (gmpy2.powmod(slope, 2, self.p) - 2 * p.x) % self.p
        y3 = (slope * (p.x - x3) - p.y) % self.p

        return Point(x3, y3, self.curve)

    def scalar_mult(
        self, k: Union[int, gmpy2.mpz], point: Optional[Point] = None
    ) -> Point:
        if point is None:
            point = self.G

        k_mpz = gmpy2.mpz(k) % self.n

        if k_mpz == 0 or point.is_infinity:
            return Point.infinity(self.curve)

        result = Point.infinity(self.curve)
        addend = point

        while k_mpz > 0:
            if k_mpz.is_odd():
                result = self.point_add(result, addend)
            addend = self.point_double(addend)
            k_mpz >>= 1

        return result

    def sign(
        self, private_key: Union[int, gmpy2.mpz], message_hash: Union[int, gmpy2.mpz]
    ) -> Tuple[int, int]:
        d = gmpy2.mpz(private_key)
        z = gmpy2.mpz(message_hash)

        while True:
            k = gmpy2.mpz(self.random_scalar())
            R = self.scalar_mult(k, self.G)
            r = R.x % self.n
            if r == 0:
                continue

            k_inv = gmpy2.invert(k, self.n)
            s = (k_inv * (z + r * d)) % self.n
            if s == 0:
                continue

            return int(r), int(s)

    def verify(
        self,
        public_key: Point,
        message_hash: Union[int, gmpy2.mpz],
        signature: Tuple[int, int],
    ) -> bool:
        if not isinstance(public_key, Point) or public_key.is_infinity:
            return False

        r, s = map(gmpy2.mpz, signature)
        z = gmpy2.mpz(message_hash)

        if not (0 < r < self.n and 0 < s < self.n):
            return False

        w = gmpy2.invert(s, self.n)
        u1 = (z * w) % self.n
        u2 = (r * w) % self.n

        P = self.point_add(
            self.scalar_mult(u1, self.G), self.scalar_mult(u2, public_key)
        )

        if P.is_infinity:
            return False

        return P.x % self.n == r
