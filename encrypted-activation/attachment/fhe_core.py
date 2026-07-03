from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass
from typing import List

Q_BITS = 64
Q = 1 << Q_BITS
MASK = Q - 1

Lvl0_n, Lvl1_n = 622, 1024
k, n = 2, 512
P = 5
Δ = Q // P
Bgbit, l = 19, 1
basebit, t = 12, 2
α0, α1 = pow(2.0, -45), pow(2.0, -52)
α0_u64, α1_u64 = round(α0 * Q), round(α1 * Q)
N = Lvl1_n

rng = random.SystemRandom()
SEED_BYTES = 32

_noise = lambda σ: int(round(σ * rng.gauss(0.0, 1.0)))
_u64 = lambda x: x & MASK
_rand_u64 = lambda: rng.getrandbits(64)
_rand_bit = lambda: rng.getrandbits(1)
_rand_seed = lambda: bytes(rng.getrandbits(8) for _ in range(SEED_BYTES))

def decompress(seed):
    if len(seed) != SEED_BYTES:
        raise ValueError(f"expected a {SEED_BYTES}-byte seed")
    stream = hashlib.shake_256(seed + N.to_bytes(8, "little")).digest(8 * N)
    return [int.from_bytes(stream[8 * i:8 * (i + 1)], "little") for i in range(N)]

def poly_add(a: List[int], b: List[int]) -> List[int]:
    return [_u64(x + y) for x, y in zip(a, b)]

_SLOT = 128
_SLOTMASK = (1 << _SLOT) - 1

def _pack(p: List[int]) -> int:
    x = 0
    for i in range(n - 1, -1, -1):
        x = (x << _SLOT) | (p[i] & _SLOTMASK)
    return x

def poly_mul(a: List[int], b: List[int]) -> List[int]:
    A, B = _pack(a), _pack(b)
    C = A * B
    out = [0] * n
    for i in range(2 * n - 1):
        c = (C >> (i * _SLOT)) & _SLOTMASK
        if c == 0:
            continue
        if i < n:
            out[i] = (out[i] + c) & MASK
        else:
            out[i - n] = (out[i - n] - c) & MASK
    return out
    
# ----------------------------------------------------------------------------
# Keys
# ----------------------------------------------------------------------------
@dataclass
class SecretKey:
    lvl0: List[int] 
    lvl1: List[int] 

@dataclass
class LWECiphertext:
    a: List[int]
    b: int

@dataclass
class GLWECiphertext:
    ã: List[List[int]]            # k mask polynomials
    b̃: List[int]                  # body polynomial

@dataclass
class BootstrapKey:
    rows: List[List[GLWECiphertext]]
    Bgbit: int = Bgbit
    l: int = l

@dataclass
class KeySwitchKey:
    rows: List[List["LWECiphertext"]]
    basebit: int = basebit
    t: int = t

# ----------------------------------------------------------------------------
# Low-level encrypt primitives
# ----------------------------------------------------------------------------
def lwe_encrypt(a, s, μ, σ):
    b = μ + _noise(σ)
    for ai, si in zip(a, s):
        b = (b + ai * si) & MASK
    return LWECiphertext(a=a, b=_u64(b))

def glwe_encrypt(s̃, μ, σ):
    ã = [[_rand_u64() for _ in range(n)] for _ in range(k)]
    aS = [0] * n
    for _, __ in zip(ã, s̃):
        aS = poly_add(aS, poly_mul(_, __))
    b̃ = [(aS[i] + μ[i] + _noise(σ)) & MASK for i in range(n)]
    return GLWECiphertext(ã=ã, b̃=b̃)

# ----------------------------------------------------------------------------
# Keygen
# ----------------------------------------------------------------------------
def gen_bsk(sk):
    Bg = 1 << Bgbit
    gadget = [Q // (Bg ** j) for j in range(1, l + 1)]
    rows, poly_sk = [], [sk.lvl1[i * n:(i + 1) * n] for i in range(k)]
    for si in sk.lvl0:
        RGSW = []
        for _part in range(k + 1):
            for g in gadget:
                if _part < k:
                    scaled = _u64(-(si * g))
                    mu = [_u64(scaled * coeff) for coeff in poly_sk[_part]]
                else:
                    mu = [_u64(si * g)] + [0] * (n - 1)
                RGSW.append(glwe_encrypt(poly_sk, mu, α1_u64))
        rows.append(RGSW)
    return BootstrapKey(rows=rows, Bgbit=Bgbit, l=l)

def gen_ksk(sk):
    Bk = 1 << basebit
    rows = []
    for si in sk.lvl1:
        per_level = []
        for j in range(1, t + 1):
            scaled = _u64(si * (Q // (Bk ** j)))
            a = [_rand_u64() for _ in range(Lvl0_n)]
            per_level.append(lwe_encrypt(a, sk.lvl0, scaled, α0_u64))
        rows.append(per_level)
    return KeySwitchKey(rows=rows, basebit=basebit, t=t)

def keygen():
    lvl0_sk = [_rand_bit() for _ in range(Lvl0_n)]
    lvl1_sk = [_rand_bit() for _ in range(Lvl1_n)]
    sk = SecretKey(lvl0=lvl0_sk, lvl1=lvl1_sk)
    bsk, ksk = gen_bsk(sk), gen_ksk(sk)
    return sk, bsk, ksk

# ----------------------------------------------------------------------------
# Message encrypt / decrypt 
# ----------------------------------------------------------------------------
def encrypt_ciphertext(sk, m, seed = None):
    μ = (Δ * (m % P)) & MASK
    if seed is None:
        seed = _rand_seed()
    a = decompress(seed)
    return seed, lwe_encrypt(a, sk.lvl1, μ, α1_u64)

def decrypt_ciphertext(sk, ct):
    phase = ct.b
    for ai, si in zip(ct.a, sk.lvl1):
        phase = (phase - ai * si) & MASK
    return (((phase & MASK) * P + (Q >> 1)) >> Q_BITS) % P

# ----------------------------------------------------------------------------
# Serialization  (all little-endian u64)
# ----------------------------------------------------------------------------
_u64le = lambda v: (v & MASK).to_bytes(8, "little")
_rd = lambda buf, off: (int.from_bytes(buf[off:off+8], "little"), off + 8)

def serialize_client_key(sk: SecretKey) -> bytes:
    out = bytearray()
    out += _u64le(Lvl0_n)
    out += _u64le(Lvl1_n)
    for coeff in sk.lvl0:
        out += _u64le(coeff)
    for coeff in sk.lvl1:
        out += _u64le(coeff)
    return bytes(out)

def serialize_lwe_ciphertext(c: LWECiphertext) -> bytes:
    out = bytearray()
    out += _u64le(len(c.a))
    out += _u64le(0)
    for ai in c.a:
        out += _u64le(ai)
    out += _u64le(c.b)
    return bytes(out)

def serialize_glwe(ct: GLWECiphertext) -> bytes:
    out = bytearray()
    out += _u64le(len(ct.ã))
    out += _u64le(len(ct.b̃))
    for poly in ct.ã:
        for v in poly:
            out += _u64le(v)
    for v in ct.b̃:
        out += _u64le(v)
    return bytes(out)

def serialize_bsk(bsk: BootstrapKey) -> bytes:
    out = bytearray()
    out += _u64le(bsk.Bgbit)
    out += _u64le(bsk.l)
    out += _u64le(len(bsk.rows))
    for trgsw in bsk.rows:
        out += _u64le(len(trgsw))
        for r in trgsw:
            out += serialize_glwe(r)
    return bytes(out)

def serialize_ksk(ksk: KeySwitchKey) -> bytes:
    out = bytearray()
    out += _u64le(ksk.basebit)
    out += _u64le(ksk.t)
    out += _u64le(len(ksk.rows))
    for per_level in ksk.rows:
        out += _u64le(len(per_level))
        for c in per_level:
            out += serialize_lwe_ciphertext(c)
    return bytes(out)

def parse_lwe_ciphertext(buf: bytes) -> LWECiphertext:
    off = 0
    lwe_dim, off = _rd(buf, off)
    _q, off = _rd(buf, off)
    a = []
    for _ in range(lwe_dim):
        v, off = _rd(buf, off)
        a.append(v)
    b, off = _rd(buf, off)
    return LWECiphertext(a=a, b=b)

def parse_client_key(buf: bytes) -> SecretKey:
    off = 0
    lvl0_n, off = _rd(buf, off)
    lvl1_n, off = _rd(buf, off)
    lvl0, lvl1 = [], []
    for _ in range(lvl0_n):
        v, off = _rd(buf, off)
        lvl0.append(v)
    for _ in range(lvl1_n):
        v, off = _rd(buf, off)
        lvl1.append(v)
    return SecretKey(lvl0=lvl0, lvl1=lvl1)
