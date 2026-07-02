import hashlib


POW_ALGORITHM = "sha256"


def has_leading_zero_bits(digest: bytes, difficulty: int) -> bool:
    if not 0 <= difficulty <= len(digest) * 8:
        raise ValueError("difficulty is outside the digest size")

    full_bytes, remaining_bits = divmod(difficulty, 8)
    if any(digest[:full_bytes]):
        return False
    if remaining_bits == 0:
        return True

    return digest[full_bytes] >> (8 - remaining_bits) == 0


def pow_digest(challenge: bytes, nonce: int) -> bytes:
    if not 0 <= nonce < 1 << 64:
        raise ValueError("nonce must be an unsigned 64-bit integer")
    return hashlib.sha256(challenge + nonce.to_bytes(8, "big")).digest()


def verify_pow(challenge: bytes, nonce: int, difficulty: int) -> bool:
    return has_leading_zero_bits(pow_digest(challenge, nonce), difficulty)


def solve_pow(challenge: bytes, difficulty: int) -> int:
    prefix = hashlib.sha256(challenge)
    for nonce in range(1 << 64):
        candidate = prefix.copy()
        candidate.update(nonce.to_bytes(8, "big"))
        if has_leading_zero_bits(candidate.digest(), difficulty):
            return nonce

    raise RuntimeError("PoW nonce space exhausted")
