#!/usr/bin/env python3
import hashlib
import os
import struct
import uuid as _uuid_mod

DELTA = 0x9E3779B9

FLAG_PREFIX = os.environ.get("WHISPER_FLAG_PREFIX", "R3CTF")
FLAG_TEMPLATE = os.environ.get("WHISPER_FLAG_TEMPLATE", "whisper-rcard-0click")
FLAG_KEY = os.environ.get("WHISPER_FLAG_KEY", "wh1sper-st3go-2026")

def _to_u32(data, include_length=False):
    length = len(data)
    n = length >> 2
    if length & 3:
        n += 1
    if include_length:
        v = [0] * (n + 1)
        v[n] = length
    else:
        v = [0] * n
    for i in range(length):
        v[i >> 2] |= data[i] << ((i & 3) << 3)
    return v

def _to_bytes(v, include_length=False):
    length = len(v)
    n = length << 2
    if include_length:
        m = v[length - 1]
        n -= 4
        assert not (m < n - 3 or m > n)
        n = m
    result = bytearray(n)
    for i in range(n):
        result[i] = (v[i >> 2] >> ((i & 3) << 3)) & 0xFF
    return bytes(result)

def _mx(sum_, y, z, p, e, k):
    return (
        (((z >> 5) ^ (y << 2)) + ((y >> 3) ^ (z << 4)))
        ^ ((sum_ ^ y) + (k[(p & 3) ^ e] ^ z))
    ) & 0xFFFFFFFF

def _fixk(k):
    key = list(k)
    while len(key) < 4:
        key.append(0)
    return key

def _xxtea_encrypt(v, k):
    v = list(v)
    length = len(v)
    n = length - 1
    key = _fixk(k)
    z = v[n]
    sum_ = 0
    q = 6 + 52 // length
    while q > 0:
        sum_ = (sum_ + DELTA) & 0xFFFFFFFF
        e = (sum_ >> 2) & 3
        for p in range(n):
            y = v[p + 1]
            v[p] = (v[p] + _mx(sum_, y, z, p, e, key)) & 0xFFFFFFFF
            z = v[p]
        y = v[0]
        v[n] = (v[n] + _mx(sum_, y, z, n, e, key)) & 0xFFFFFFFF
        z = v[n]
        q -= 1
    return v

def _xxtea_decrypt(v, k):
    v = list(v)
    length = len(v)
    n = length - 1
    key = _fixk(k)
    y = v[0]
    q = 6 + 52 // length
    sum_ = (q * DELTA) & 0xFFFFFFFF
    while sum_ != 0:
        e = (sum_ >> 2) & 3
        p = n
        while p > 0:
            z = v[p - 1]
            v[p] = (v[p] - _mx(sum_, y, z, p, e, key)) & 0xFFFFFFFF
            y = v[p]
            p -= 1
        z = v[n]
        v[0] = (v[0] - _mx(sum_, y, z, 0, e, key)) & 0xFFFFFFFF
        y = v[0]
        sum_ = (sum_ - DELTA) & 0xFFFFFFFF
    return v

def xxtea_encrypt(data, key):
    return _to_bytes(_xxtea_encrypt(_to_u32(data, False), _to_u32(key.encode(), False)), False)

def xxtea_decrypt(data, key):
    return _to_bytes(_xxtea_decrypt(_to_u32(data, False), _to_u32(key.encode(), False)), False)

def _chacha_block(key_bytes, data):
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

    h = hashlib.sha256(key_bytes).digest()
    cipher = ChaCha20Poly1305(h[:32])
    return cipher.encrypt(h[-12:], data, None)

def encode_uuid(template, key, team_id, with_hyphen=True):
    sha1_digest = hashlib.sha1(template.encode()).digest()
    hash_slice = bytearray(sha1_digest[2:18])
    team_id_bytes = struct.pack("<q", team_id)
    encrypted = xxtea_encrypt(team_id_bytes, key)
    encrypted_slice = encrypted[:8].ljust(8, b"\x00")
    rand_bytes = b"\x00\x00\x00\x00"
    for i in range(8):
        if i % 2 == 0:
            hash_slice[i * 2] ^= rand_bytes[i // 2]
        hash_slice[i * 2 + 1] ^= encrypted_slice[i]
    ct = _chacha_block(key.encode(), bytes(hash_slice))
    u = _uuid_mod.UUID(bytes=ct[:16])
    return str(u) if with_hyphen else u.hex

def decode_uuid(template, key, flag):
    s = flag.strip()
    if "{" in s and s.endswith("}"):
        s = s[s.index("{") + 1 : -1]
    u = _uuid_mod.UUID(s)
    block = _chacha_block(key.encode(), u.bytes)[:16]
    sha1_digest = hashlib.sha1(template.encode()).digest()
    hash_slice = sha1_digest[2:18]
    dec = bytearray(8)
    for i in range(8):
        if i % 2 != 0:
            if hash_slice[i * 2] != block[i * 2]:
                raise ValueError(f"flag data broken at position {i * 2}")
        dec[i] = hash_slice[i * 2 + 1] ^ block[i * 2 + 1]
    decrypted = xxtea_decrypt(bytes(dec), key)
    return struct.unpack("<q", decrypted[:8])[0]

def make_flag(team_id, template=None, key=None):
    return "%s{%s}" % (
        FLAG_PREFIX,
        encode_uuid(template or FLAG_TEMPLATE, key or FLAG_KEY, int(team_id)),
    )

def flag_team_id(flag, template=None, key=None):
    return decode_uuid(template or FLAG_TEMPLATE, key or FLAG_KEY, flag)
