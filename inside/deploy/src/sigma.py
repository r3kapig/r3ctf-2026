from sage.all import *
from hashlib import sha256


p = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
a = 0x0
b = 0x7
q = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
E = EllipticCurve(GF(p), [a, b])
O = E(0)
G = E(0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798, 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8)


def point2tuple(P):
    if P == O:
        return 0
    else:
        return (P.xy()[0], P.xy()[1])

def tuple2point(t):
    return E(t)


class CurveHomomorphism:
    def __init__(self, Gs):
        self.Gs = Gs
        self.n, self.m = len(Gs[0]), len(Gs)

    def __str__(self):
        return f"CurveHomomorphism(Gs={self.Gs})"
    
    def __call__(self, x):
        assert len(x) == self.n
        return [sum(x[i] * self.Gs[j][i] for i in range(self.n)) for j in range(self.m)]

    @staticmethod
    def compose(phi1, phi2):
        n = phi1.n + phi2.n
        m = phi1.m + phi2.m
        Gs = [[O]*n for _ in range(m)]
        for i in range(phi1.m):
            for j in range(phi1.n):
                Gs[i][j] = phi1.Gs[i][j]
        for i in range(phi2.m):
            for j in range(phi2.n):
                Gs[phi1.m+i][phi1.n+j] = phi2.Gs[i][j]
        return CurveHomomorphism(Gs)


class MaurerProof:
    def __init__(self, st, wit=None):
        self.st, self.wit = st, wit
    
    @staticmethod
    def oracle(buf):
        return int(sha256(buf).hexdigest(), 16) % q

    def prove(self):
        assert self.wit is not None
        phi, Y = self.st
        x = self.wit

        r = [randint(0, q-1) for _ in range(phi.n)]
        R = phi(r)
        c = self.oracle(str(R).encode() + str(Y).encode() + str(phi).encode())
        z = [(r[i] + c * x[i]) % q for i in range(phi.n)]
        return R, z

    def verify(self, proof):
        try:
            phi, Y = self.st
            R, z = proof
            assert len(R) == len(Y) == phi.m
            c = self.oracle(str(R).encode() + str(Y).encode() + str(phi).encode())
            return all(Zi == Ri + c*Yi for Zi, Ri, Yi in zip(phi(z), R, Y))
        except:
            return False