from fastapi import APIRouter, HTTPException, Header
from database import reset_db, init_db
from config import ADMIN_TOKEN

router = APIRouter(prefix="/admin", tags=["admin"])

def _check_admin(authorization: str):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing admin token")
    token = authorization[7:]
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid admin token")

@router.post("/reset")
async def reset(authorization: str = Header(...)):

    _check_admin(authorization)
    reset_db()
    init_db()
    return {"status": "reset", "message": "All state wiped. Fresh state ready."}

@router.get("/health")
async def health():
    return {"status": "ok", "service": "whisper-backend"}
