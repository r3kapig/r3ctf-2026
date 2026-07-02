import hashlib
import os
import secrets
import time
from typing import Optional

from fastapi import HTTPException, Header
from config import TOKEN_TTL
from database import get_connection

def _now() -> int:
    return int(time.time())

_PBKDF2_ITERS = 100_000
_PBKDF2_HASH  = "sha256"
_SALT_BYTES   = 16

def hash_password(password: str) -> str:

    salt = os.urandom(_SALT_BYTES)
    dk = hashlib.pbkdf2_hmac(_PBKDF2_HASH, password.encode(), salt, _PBKDF2_ITERS)
    return salt.hex() + "$" + dk.hex()

def verify_password(password: str, stored: str) -> bool:

    if not stored or "$" not in stored:
        return False
    salt_hex, dk_hex = stored.split("$", 1)
    try:
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(dk_hex)
    except ValueError:
        return False
    candidate = hashlib.pbkdf2_hmac(_PBKDF2_HASH, password.encode(), salt, _PBKDF2_ITERS)
    return secrets.compare_digest(candidate, expected)

def create_token(user_id: str) -> str:
    token = secrets.token_hex(32)
    now = _now()
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO sessions(token, user_id, created_at, expires_at) VALUES(?,?,?,?)",
            (token, user_id, now, now + TOKEN_TTL),
        )
    conn.close()
    return token

def get_user_id_from_token(token: str) -> Optional[str]:
    conn = get_connection()
    row = conn.execute(
        "SELECT user_id, expires_at FROM sessions WHERE token=?", (token,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    if _now() > row["expires_at"]:
        return None
    return row["user_id"]

async def require_auth(authorization: str = Header(...)) -> str:

    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization[7:]
    user_id = get_user_id_from_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return user_id
