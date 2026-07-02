import uuid
import time
from fastapi import APIRouter, HTTPException, Depends

from models import RegisterRequest, LoginRequest, TokenResponse
from auth import (
    create_token, require_auth,
    hash_password, verify_password,
)
from database import get_connection
from config import CTF_MODE

router = APIRouter(prefix="/auth", tags=["auth"])

def _now() -> int:
    return int(time.time())

@router.post("/register", response_model=TokenResponse)
async def register(body: RegisterRequest):

    if not body.password:
        raise HTTPException(status_code=422, detail="password must not be empty")

    conn = get_connection()
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE phone=?", (body.phone,)
    ).fetchone()

    if row is None:
        if not body.handle or not body.display_name:
            conn.close()
            raise HTTPException(status_code=400, detail="handle and display_name required for new users")
        conflict = conn.execute(
            "SELECT id FROM users WHERE handle=?", (body.handle,)
        ).fetchone()
        if conflict:
            conn.close()
            raise HTTPException(status_code=409, detail="handle already taken")

        user_id = str(uuid.uuid4())
        pw_hash = hash_password(body.password)

        is_victim = bool(body.is_victim) or (CTF_MODE and body.display_name.startswith("Whisper Victim"))
        conn.execute(
            "INSERT INTO users(id, handle, display_name, phone, bio, avatar_seed, created_at, password_hash, is_victim) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (user_id, body.handle, body.display_name, body.phone, "", 0, _now(), pw_hash, int(is_victim)),
        )
        conn.commit()
    else:
        if not verify_password(body.password, row["password_hash"]):
            conn.close()
            raise HTTPException(status_code=409, detail="phone already registered")
        user_id = row["id"]

    conn.close()
    token = create_token(user_id)
    return TokenResponse(token=token, user_id=user_id)

@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):

    if not body.password:
        raise HTTPException(status_code=422, detail="password must not be empty")

    conn = get_connection()
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE phone=?", (body.phone,)
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="No account for this phone")

    if not verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect password")

    token = create_token(row["id"])
    return TokenResponse(token=token, user_id=row["id"])

@router.post("/logout")
async def logout(user_id: str = Depends(require_auth)):

    conn = get_connection()
    with conn:
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    conn.close()
    return {"message": "logged out"}
