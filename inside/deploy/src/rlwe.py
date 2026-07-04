from sage.all import *
from sigma import CurveHomomorphism, MaurerProof, q, G, O


R, x = ZZ["x"].objgen()
qq = 3329
n = 256
f = x**n + 1

def rlwe_gen():
    def f2l(f):
        return f.list() + [0]*(n-len(f.list()))

    a = R([randint(-qq//2, qq//2) for _ in range(n)])
    s = R([randint(-1, 1) for _ in range(n)])
    e = R([randint(-1, 1) for _ in range(n)])
    b = (a*s + e) % f % qq
    k = ((a*s + e) % f - b) // qq

    assert (a*s + e) % f == (b + k*qq)
    return (f2l(a), f2l(b)), (f2l(s), f2l(e), f2l(k))


class RLWEProof:
    def __init__(self, st, wit=None):
        self.st, self.wit = st, wit
    
    def __str__(self):
        return f"RLWEProof(st={self.st}, wit={self.wit})"

    @staticmethod
    def bitdecom(x, nbit):
        assert 0 <= x and x <= 2**nbit-1
        return [((x >> i) & 1) for i in range(nbit)]
    
    def encode(self, aux, crs):
        a, b = self.st
        
        ### (sij)
        Y0, Gs0 = list(), list()
        Ax = [sum(a[j]*crs[(i+j)%n] for j in range(n)) for i in range(n)]
        Bx = sum(b[i]*crs[i] for i in range(n))
        Ex = sum(sum(2**j*aux[1][i][j] for j in range(2))-1*crs[i] for i in range(n))
        Kx = sum(aux[2][i] for i in range(n))
        Y0.extend([qq*Kx + Bx - Ex + 1*sum(Ax[i] for i in range(n))])
        Gs0.extend(
            [sum([[2**j*Ax[i] for j in range(2)] for i in range(n)], [])]
        )
        for j in range(2):
            Y0.extend([aux[0][i][j] for i in range(n)])
            Gs0.extend(
                [[O]*i*2 + [O]*j + [crs[i]] + [O]*(2-j-1) + [O]*2*(n-i-1) for i in range(n)]
            )
            Y0.extend([aux[0][i][j] for i in range(n)])
            Gs0.extend(
                [[O]*i*2 + [O]*j + [aux[0][i][j]] + [O]*(2-j-1) + [O]*2*(n-i-1) for i in range(n)]  
            )
        phi0 = CurveHomomorphism(Gs0)

        ### (eij)
        Y1, Gs1 = list(), list()
        for j in range(2):
            Y1.extend([aux[1][i][j] for i in range(n)])
            Gs1.extend(
                [[O]*i*2 + [O]*j + [crs[i]] + [O]*(2-j-1) + [O]*2*(n-i-1) for i in range(n)]
            )
            Y1.extend([aux[1][i][j] for i in range(n)])
            Gs1.extend(
                [[O]*i*2 + [O]*j + [aux[1][i][j]] + [O]*(2-j-1) + [O]*2*(n-i-1) for i in range(n)]
            )
        phi1 = CurveHomomorphism(Gs1)

        ### (ki)
        Y2, Gs2 = list(), list()
        Y2.extend([aux[2][i] for i in range(n)])
        Gs2.extend(
            [[O]*i + [crs[i]] + [O]*(n-i-1) for i in range(n)]
        )
        phi2 = CurveHomomorphism(Gs2)

        return (phi0, Y0), (phi1, Y1), (phi2, Y2)

    def prove(self, crs):
        assert self.wit is not None
        s, e, k = self.wit
        
        ss = [self.bitdecom(si+1, nbit=2) for si in s]
        ee = [self.bitdecom(ei+1, nbit=2) for ei in e]

        aux = [
            [[ss[i][j]*crs[i] for j in range(2)] for i in range(n)],
            [[ee[i][j]*crs[i] for j in range(2)] for i in range(n)],
            [k[i]*crs[i] for i in range(n)],
        ]
        sts = self.encode(aux, crs)
        wits = [sum(ss, []), sum(ee, []), k]
        proof = [
            MaurerProof(st=st, wit=wit).prove()
            for st, wit in zip(sts, wits)
        ]
        return aux, proof

    def verify(self, crs, aux, proof):
        try:
            sts = self.encode(aux, crs)
            assert len(sts) == len(proof)
            return all(
                MaurerProof(st=st).verify(proof)
                for st, proof in zip(sts, proof)
            )
        except:
            return False