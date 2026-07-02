from typing import List
import hashlib
import struct

HASH_INPUT_DELIMITER = b"$"


def sha512_256_util(h, in_data: List[bytes]) -> bytes:
    if not in_data:
        return None
    data = bytearray()
    data.extend(struct.pack("<Q", len(in_data)))
    for b in in_data:
        data.extend(b)
        data.extend(HASH_INPUT_DELIMITER)
        data.extend(struct.pack("<Q", len(b)))
    h.update(data)
    return h.digest()

def sha512_256(*in_data: bytes) -> bytes:
    h = hashlib.new("sha512_256")
    return sha512_256_util(h, list(in_data))

def sha512_256i(*in_data: int) -> int:
    h = hashlib.new("sha512_256")
    ptrs = []
    for i in in_data:
        i = int(i)
        mag = abs(i).to_bytes((abs(i).bit_length() + 7) // 8, "big") if i else b""
        sign = 1 if i > 0 else -1 if i < 0 else 0
        ptrs.append(mag + bytes([sign & 0xFF]))
    hashed_bytes = sha512_256_util(h, ptrs)
    return int.from_bytes(hashed_bytes, "big")

def sha512_256i_tagged(tag: bytes, *in_data: int) -> int:
    tag_bz = sha512_256(tag)
    h = hashlib.new("sha512_256")
    h.update(tag_bz)
    h.update(tag_bz)
    ptrs = []
    for i in in_data:
        i = int(i)
        mag = abs(i).to_bytes((abs(i).bit_length() + 7) // 8, "big") if i else b""
        sign = 1 if i > 0 else -1 if i < 0 else 0
        ptrs.append(mag + bytes([sign & 0xFF]))
    hashed_bytes = sha512_256_util(h, ptrs)
    return int.from_bytes(hashed_bytes, "big")
