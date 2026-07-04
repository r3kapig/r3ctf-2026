from sage.all import *
import os, ast, signal

from sigma import q, G, E, tuple2point, point2tuple
from rlwe import rlwe_gen, RLWEProof, n


def proof_of_work():
    import random, string, hashlib

    ss = ''.join(random.choices(string.ascii_letters + string.digits, k=20))
    sh = hashlib.sha256(ss.encode()).hexdigest()
    print(f"|    sha256(XXXX + {ss[4:]}) == {sh}")
    prefix = input("|    XXXX>")
    return prefix == ss[:4]

assert proof_of_work()
signal.alarm(1800)


MENU = '''==========
|   [C]RS
|[R]LWE
| [P]roof of Knowledge
|    [T]ake a break
|  [Q]uit
=========='''

crs, st = None, None

while True:
    print(MENU)
    inp = input(">").strip().lower()
    try:
        if inp == "q":
            raise Exception("ok~")

        elif inp == "c":
            tau = int(os.urandom(32).hex(), 16) % q
            crs = [pow(tau, i, q)*G for i in range(n)]
            del tau
            print(f"crs = {list(map(point2tuple, crs))}")

        elif inp == "r":
            st, _ = rlwe_gen()
            print(f"st = {st}")

        elif inp == "p":
            if crs is None or st is None:
                print("nah...")
                continue
            aux = ast.literal_eval(input("aux>"))
            proof = ast.literal_eval(input("proof>"))

            aux = [
                [[E(aux[0][i][j]) for j in range(2)] for i in range(n)],
                [[E(aux[1][i][j]) for j in range(2)] for i in range(n)],
                [E(aux[2][i]) for i in range(n)],
            ]
            proof = [
                (list(map(tuple2point, R)), z) for R, z in proof
            ]

            if RLWEProof(st).verify(crs, aux, proof):
                print("Congratulations!")
                print(f"{os.environ.get('FLAG')}")
                print("Hope you enjoy!")
                raise Exception

        elif inp == "t":
            print("not today.")
        
        else:
            raise Exception("oh...")
    except:
        exit(0)