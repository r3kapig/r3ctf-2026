from fastapi import APIRouter, HTTPException, Depends, Query
from auth import require_auth
from database import get_connection
from models import UserProfile, UserPublic, UpdateProfile

router = APIRouter(prefix="/users", tags=["users"])

def _row_to_public(row) -> UserPublic:
    return UserPublic(
        id=row["id"],
        handle=row["handle"],
        display_name=row["display_name"],
        bio=row["bio"] or "",
        avatar_seed=row["avatar_seed"] or 0,
    )

def _row_to_profile(row) -> UserProfile:
    return UserProfile(
        id=row["id"],
        handle=row["handle"],
        display_name=row["display_name"],
        phone=row["phone"],
        bio=row["bio"] or "",
        avatar_seed=row["avatar_seed"] or 0,
        created_at=row["created_at"],
    )

@router.get("/me", response_model=UserProfile)
async def get_me(user_id: str = Depends(require_auth)):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _row_to_profile(row)

@router.patch("/me", response_model=UserProfile)
async def update_me(body: UpdateProfile, user_id: str = Depends(require_auth)):
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found")

    updates = {}
    if body.display_name is not None:
        updates["display_name"] = body.display_name
    if body.bio is not None:
        updates["bio"] = body.bio
    if body.avatar_seed is not None:
        updates["avatar_seed"] = body.avatar_seed

    if updates:
        set_clause = ", ".join(f"{k}=?" for k in updates)
        values = list(updates.values()) + [user_id]
        with conn:
            conn.execute(f"UPDATE users SET {set_clause} WHERE id=?", values)

    row = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    conn.close()
    return _row_to_profile(row)

@router.get("/search", response_model=list[UserPublic])
async def search_users(
    q: str = Query(..., min_length=1),
    user_id: str = Depends(require_auth),
):

    conn = get_connection()
    pattern = f"%{q}%"
    rows = conn.execute(
        "SELECT * FROM users WHERE id != ? AND ("
        "(is_victim = 0 AND (handle LIKE ? OR display_name LIKE ?)) "
        "OR (is_victim = 1 AND handle = ? COLLATE NOCASE)"
        ") LIMIT 30",
        (user_id, pattern, pattern, q),
    ).fetchall()
    conn.close()
    return [_row_to_public(r) for r in rows]

@router.get("/{user_id_or_handle}", response_model=UserPublic)
async def get_user(
    user_id_or_handle: str,
    _caller: str = Depends(require_auth),
):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM users WHERE id=? OR handle=?",
        (user_id_or_handle, user_id_or_handle),
    ).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    return _row_to_public(row)
