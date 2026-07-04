#!/usr/bin/env python3
"""
UUID Stego Flag Generator / Decoder
Based on ret2script's UUIDStego algorithm (audit.rs).

Same template + key + team_id always produces the same flag.
Uses deterministic salt (zeros) instead of random bytes.
"""

import hashlib
import struct
import sys
import uuid as _uuid_mod


DELTA = 0x9E3779B9


def _to_u32(data: bytes, include_length: bool = False) -> list[int]:
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


def _to_bytes(v: list[int], include_length: bool = False) -> bytes:
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


def _mx(sum_: int, y: int, z: int, p: int, e: int, k: list[int]) -> int:
    return (
        (((z >> 5) ^ (y << 2)) + ((y >> 3) ^ (z << 4)))
        ^ ((sum_ ^ y) + (k[(p & 3) ^ e] ^ z))
    ) & 0xFFFFFFFF


def _fixk(k: list[int]) -> list[int]:
    key = list(k)
    while len(key) < 4:
        key.append(0)
    return key


def _xxtea_encrypt(v: list[int], k: list[int]) -> list[int]:
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


def _xxtea_decrypt(v: list[int], k: list[int]) -> list[int]:
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


def xxtea_encrypt(data: bytes, key: str) -> bytes:
    """XXTEA encrypt bytes with string key (matches ret2script)."""
    key_bytes = key.encode()
    v = _to_u32(data, False)
    k = _to_u32(key_bytes, False)
    encrypted = _xxtea_encrypt(v, k)
    return _to_bytes(encrypted, False)


def xxtea_decrypt(data: bytes, key: str) -> bytes:
    """XXTEA decrypt bytes with string key (matches ret2script)."""
    key_bytes = key.encode()
    v = _to_u32(data, False)
    k = _to_u32(key_bytes, False)
    decrypted = _xxtea_decrypt(v, k)
    return _to_bytes(decrypted, False)


def _chacha20_poly1305_encrypt(key_bytes: bytes, data: bytes) -> bytes:
    """ChaCha20-Poly1305 encrypt. Returns ciphertext || tag (32 bytes for 16-byte input)."""
    from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

    h = hashlib.sha256(key_bytes).digest()
    chacha_key = h[:32]
    nonce = h[-12:]
    cipher = ChaCha20Poly1305(chacha_key)
    return cipher.encrypt(nonce, data, None)


def encode_uuid(template: str, key: str, team_id: int, with_hyphen: bool = True) -> str:
    """
    Generate a UUID flag embedding the team_id.
    Same (template, key, team_id) always yields the same UUID.
    """
    sha1_digest = hashlib.sha1(template.encode()).digest()
    hash_slice = bytearray(sha1_digest[2:18])

    team_id_bytes = struct.pack("<q", team_id)
    encrypted = xxtea_encrypt(team_id_bytes, key)
    encrypted_slice = encrypted[:8].ljust(8, b"\x00")

    # deterministic salt (zeros) ensures same input → same output
    rand_bytes = b"\x00\x00\x00\x00"

    for i in range(8):
        if i % 2 == 0:
            hash_slice[i * 2] ^= rand_bytes[i // 2]
        hash_slice[i * 2 + 1] ^= encrypted_slice[i]

    ct = _chacha20_poly1305_encrypt(key.encode(), bytes(hash_slice))
    uuid_bytes = ct[:16]

    u = _uuid_mod.UUID(bytes=uuid_bytes)
    return str(u) if with_hyphen else u.hex


def decode_uuid(template: str, key: str, flag: str) -> int:
    """
    Extract the team_id from a UUID flag.
    Works with both hyphenated and non-hyphenated UUIDs.
    """
    u = _uuid_mod.UUID(flag)
    data_slice = u.bytes

    ct = _chacha20_poly1305_encrypt(key.encode(), data_slice)
    block = ct[:16]

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


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="UUID Stego Flag Generator / Decoder")
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encode", help="Generate a UUID flag from team_id")
    enc.add_argument("template", help="Template string")
    enc.add_argument("key", help="Secret key")
    enc.add_argument("team_id", type=int, help="Team ID to embed")
    enc.add_argument("--no-hyphen", action="store_true", help="Output UUID without hyphens")

    dec = sub.add_parser("decode", help="Extract team_id from a UUID flag")
    dec.add_argument("template", help="Template string")
    dec.add_argument("key", help="Secret key")
    dec.add_argument("flag", help="UUID flag to decode")

    xxtea = sub.add_parser("xxtea", help="Encrypt team_id bytes with XXTEA (for testing)")
    xxtea.add_argument("key", help="Secret key")
    xxtea.add_argument("team_id", type=int, help="Team ID")

    args = parser.parse_args()

    if args.command == "encode":
        uid = encode_uuid(args.template, args.key, args.team_id, not args.no_hyphen)
        print(f"flag{{{uid}}}")

    elif args.command == "decode":
        tid = decode_uuid(args.template, args.key, args.flag)
        print(tid)

    elif args.command == "xxtea":
        data = struct.pack("<q", args.team_id)
        enc = xxtea_encrypt(data, args.key)
        print(enc[:8].hex())


if __name__ == "__main__":
    main()
