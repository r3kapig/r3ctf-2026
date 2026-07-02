import os
import uuid
import time

from fastapi import APIRouter, HTTPException, Depends, Request, Header
from fastapi.responses import FileResponse

from auth import require_auth
from database import get_connection
from models import AttachmentOut
from config import ATTACHMENT_DIR

router = APIRouter(prefix="/attachments", tags=["attachments"])

def _now() -> int:
    return int(time.time())

@router.post("/upload", response_model=AttachmentOut)
async def upload_attachment(
    request: Request,
    x_filename: str = Header(default="upload", alias="X-Filename"),
    x_kind: str = Header(default="file", alias="X-Kind"),
    user_id: str = Depends(require_auth),
):

    mime_type = request.headers.get("content-type", "application/octet-stream")
    mime_type = mime_type.split(";")[0].strip()

    att_id = str(uuid.uuid4())
    dest_path = os.path.join(ATTACHMENT_DIR, att_id)

    os.makedirs(ATTACHMENT_DIR, exist_ok=True)

    total_size = 0
    max_size = 50 * 1024 * 1024

    with open(dest_path, "wb") as f:
        async for chunk in request.stream():
            total_size += len(chunk)
            if total_size > max_size:
                f.close()
                os.unlink(dest_path)
                raise HTTPException(status_code=413, detail="Attachment too large (max 50 MB)")
            f.write(chunk)

    now = _now()
    conn = get_connection()
    with conn:
        conn.execute(
            "INSERT INTO attachments(id, uploader_id, filename, mime_type, kind, size, path, created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (att_id, user_id, x_filename, mime_type, x_kind, total_size, dest_path, now),
        )
    conn.close()

    return AttachmentOut(
        id=att_id,
        filename=x_filename,
        mime_type=mime_type,
        kind=x_kind,
        size=total_size,
        url=f"/attachments/{att_id}/download",
    )

def _check_attachment_access(attachment_id: str, caller: str, conn) -> None:

    allowed = conn.execute(
        "SELECT 1 FROM attachments WHERE id=? AND uploader_id=?",
        (attachment_id, caller),
    ).fetchone()
    if allowed is None:
        allowed = conn.execute(
            """SELECT 1 FROM messages m
               JOIN conversation_members cm ON cm.conversation_id = m.conversation_id
               WHERE m.attachment_id = ? AND cm.user_id = ?""",
            (attachment_id, caller),
        ).fetchone()
    if allowed is None:
        raise HTTPException(status_code=403, detail="Access denied")

@router.get("/{attachment_id}/download")
async def download_attachment(
    attachment_id: str,
    caller: str = Depends(require_auth),
):

    conn = get_connection()
    row = conn.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()

    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Attachment not found")

    _check_attachment_access(attachment_id, caller, conn)
    conn.close()

    if not os.path.isfile(row["path"]):
        raise HTTPException(status_code=404, detail="Attachment file missing from storage")

    return FileResponse(
        path=row["path"],
        media_type=row["mime_type"],
        filename=row["filename"],
    )

@router.get("/{attachment_id}", response_model=AttachmentOut)
async def get_attachment_meta(
    attachment_id: str,
    caller: str = Depends(require_auth),
):

    conn = get_connection()
    row = conn.execute("SELECT * FROM attachments WHERE id=?", (attachment_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(status_code=404, detail="Attachment not found")
    _check_attachment_access(attachment_id, caller, conn)
    conn.close()
    return AttachmentOut(
        id=row["id"],
        filename=row["filename"],
        mime_type=row["mime_type"],
        kind=row["kind"],
        size=row["size"],
        url=f"/attachments/{row['id']}/download",
    )
