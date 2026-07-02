import uuid
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Depends, Query
from auth import require_auth
from database import get_connection
from models import ConversationOut, MessageOut, MessagePreview, SendMessage, UserPublic, AttachmentOut, ReactionOut, AddReaction, CardPreview, SetPreview
from ws_manager import manager

router = APIRouter(tags=["conversations"])

def _now() -> int:
    return int(time.time())

def _get_or_create_dm(user_a: str, user_b: str) -> str:

    pair_key = "|".join(sorted([user_a, user_b]))

    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM conversations WHERE pair_key=?", (pair_key,)
    ).fetchone()
    if row:
        conv_id = row["id"]
        conn.close()
        return conv_id

    conv_id = str(uuid.uuid4())
    now = _now()
    try:
        with conn:
            conn.execute(
                "INSERT OR IGNORE INTO conversations(id, pair_key, created_at) VALUES(?,?,?)",
                (conv_id, pair_key, now),
            )
            winner = conn.execute(
                "SELECT id FROM conversations WHERE pair_key=?", (pair_key,)
            ).fetchone()
            actual_id = winner["id"]
            if actual_id == conv_id:
                conn.execute(
                    "INSERT INTO conversation_members(conversation_id, user_id) VALUES(?,?)",
                    (conv_id, user_a),
                )
                conn.execute(
                    "INSERT INTO conversation_members(conversation_id, user_id) VALUES(?,?)",
                    (conv_id, user_b),
                )
    except Exception:
        conn.close()
        raise
    conn.close()
    return actual_id

def _attachment_out(row) -> Optional[AttachmentOut]:
    if row is None:
        return None
    return AttachmentOut(
        id=row["id"],
        filename=row["filename"],
        mime_type=row["mime_type"],
        kind=row["kind"],
        size=row["size"],
        url=f"/attachments/{row['id']}/download",
    )

def _build_message_out(msg_row, conn) -> MessageOut:
    att = None
    if msg_row["attachment_id"]:
        att_row = conn.execute("SELECT * FROM attachments WHERE id=?", (msg_row["attachment_id"],)).fetchone()
        att = _attachment_out(att_row)

    reactions = conn.execute(
        "SELECT * FROM reactions WHERE message_id=?", (msg_row["id"],)
    ).fetchall()
    reaction_list = [
        ReactionOut(
            id=r["id"], message_id=r["message_id"], user_id=r["user_id"],
            emoji=r["emoji"], created_at=r["created_at"]
        ) for r in reactions
    ]

    read_rows = conn.execute(
        "SELECT user_id FROM read_receipts WHERE message_id=?", (msg_row["id"],)
    ).fetchall()
    read_by = [r["user_id"] for r in read_rows]

    preview = None
    pt = msg_row["preview_title"]
    ps = msg_row["preview_subtitle"]
    if pt is not None and ps is not None:
        preview = CardPreview(title=pt, subtitle=ps)

    return MessageOut(
        id=msg_row["id"],
        conversation_id=msg_row["conversation_id"],
        sender_id=msg_row["sender_id"],
        type=msg_row["type"],
        body=msg_row["body"],
        attachment_id=msg_row["attachment_id"],
        attachment=att,
        reply_to_id=msg_row["reply_to_id"],
        created_at=msg_row["created_at"],
        reactions=reaction_list,
        read_by=read_by,
        preview=preview,
    )

@router.get("/conversations")
async def list_conversations(user_id: str = Depends(require_auth)) -> list[ConversationOut]:
    conn = get_connection()
    conv_rows = conn.execute("""
        SELECT c.id, c.created_at
        FROM conversations c
        JOIN conversation_members cm ON c.id = cm.conversation_id
        WHERE cm.user_id = ?
        ORDER BY c.created_at DESC
    """, (user_id,)).fetchall()

    result = []
    for conv in conv_rows:
        cid = conv["id"]
        other_row = conn.execute("""
            SELECT u.* FROM users u
            JOIN conversation_members cm ON u.id = cm.user_id
            WHERE cm.conversation_id = ? AND u.id != ?
        """, (cid, user_id)).fetchone()
        if other_row is None:
            continue

        other_user = UserPublic(
            id=other_row["id"], handle=other_row["handle"],
            display_name=other_row["display_name"],
            bio=other_row["bio"] or "", avatar_seed=other_row["avatar_seed"] or 0,
        )

        last_msg_row = conn.execute("""
            SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at DESC LIMIT 1
        """, (cid,)).fetchone()
        last_msg = None
        if last_msg_row:
            last_msg = MessagePreview(
                id=last_msg_row["id"], sender_id=last_msg_row["sender_id"],
                type=last_msg_row["type"], body=last_msg_row["body"],
                created_at=last_msg_row["created_at"],
            )

        unread_row = conn.execute("""
            SELECT COUNT(*) as cnt FROM messages m
            WHERE m.conversation_id=? AND m.sender_id != ?
            AND m.id NOT IN (SELECT message_id FROM read_receipts WHERE user_id=?)
        """, (cid, user_id, user_id)).fetchone()
        unread = unread_row["cnt"] if unread_row else 0

        result.append(ConversationOut(
            id=cid, other_user=other_user, last_message=last_msg,
            unread_count=unread, created_at=conv["created_at"],
        ))

    conn.close()
    return result

@router.post("/conversations/dm")
async def open_dm(target_user_id: str, user_id: str = Depends(require_auth)):

    conn = get_connection()
    target = conn.execute("SELECT id FROM users WHERE id=? OR handle=?", (target_user_id, target_user_id)).fetchone()
    conn.close()
    if target is None:
        raise HTTPException(status_code=404, detail="Target user not found")
    if target["id"] == user_id:
        raise HTTPException(status_code=400, detail="Cannot DM yourself")

    conv_id = _get_or_create_dm(user_id, target["id"])
    return {"conversation_id": conv_id}

@router.get("/conversations/{conversation_id}/messages")
async def list_messages(
    conversation_id: str,
    before: Optional[int] = Query(None),
    limit: int = Query(50, le=200),
    user_id: str = Depends(require_auth),
) -> list[MessageOut]:
    conn = get_connection()
    member = conn.execute(
        "SELECT 1 FROM conversation_members WHERE conversation_id=? AND user_id=?",
        (conversation_id, user_id),
    ).fetchone()
    if not member:
        conn.close()
        raise HTTPException(status_code=403, detail="Not a member of this conversation")

    if before:
        rows = conn.execute("""
            SELECT * FROM messages WHERE conversation_id=? AND created_at < ?
            ORDER BY created_at DESC LIMIT ?
        """, (conversation_id, before, limit)).fetchall()
    else:
        rows = conn.execute("""
            SELECT * FROM messages WHERE conversation_id=?
            ORDER BY created_at DESC LIMIT ?
        """, (conversation_id, limit)).fetchall()

    messages = [_build_message_out(r, conn) for r in reversed(rows)]
    conn.close()
    return messages

@router.post("/messages")
async def send_message(body: SendMessage, user_id: str = Depends(require_auth)) -> MessageOut:
    conn = get_connection()
    member = conn.execute(
        "SELECT 1 FROM conversation_members WHERE conversation_id=? AND user_id=?",
        (body.conversation_id, user_id),
    ).fetchone()
    if not member:
        conn.close()
        raise HTTPException(status_code=403, detail="Not a member of this conversation")

    if body.type == "text" and not body.body:
        conn.close()
        raise HTTPException(status_code=400, detail="body required for text messages")
    if body.type == "attachment" and not body.attachment_id:
        conn.close()
        raise HTTPException(status_code=400, detail="attachment_id required for attachment messages")

    if body.attachment_id:
        att = conn.execute(
            "SELECT id FROM attachments WHERE id=? AND uploader_id=?",
            (body.attachment_id, user_id),
        ).fetchone()
        if not att:
            conn.close()
            raise HTTPException(status_code=404, detail="Attachment not found")

    msg_id = str(uuid.uuid4())
    now = _now()
    with conn:
        conn.execute(
            "INSERT INTO messages(id, conversation_id, sender_id, type, body, attachment_id, reply_to_id, created_at) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (msg_id, body.conversation_id, user_id, body.type, body.body,
             body.attachment_id, body.reply_to_id, now),
        )

    msg_row = conn.execute("SELECT * FROM messages WHERE id=?", (msg_id,)).fetchone()
    msg_out = _build_message_out(msg_row, conn)
    conn.close()

    import asyncio
    asyncio.create_task(manager.broadcast_to_conversation(
        body.conversation_id, {"type": "new_message", "message": msg_out.model_dump()}
    ))

    return msg_out

@router.post("/conversations/{conversation_id}/read")
async def mark_read(conversation_id: str, user_id: str = Depends(require_auth)):

    conn = get_connection()
    member = conn.execute(
        "SELECT 1 FROM conversation_members WHERE conversation_id=? AND user_id=?",
        (conversation_id, user_id),
    ).fetchone()
    if not member:
        conn.close()
        raise HTTPException(status_code=403, detail="Not a member")

    now = _now()
    unread_rows = conn.execute("""
        SELECT id FROM messages
        WHERE conversation_id=? AND sender_id != ?
        AND id NOT IN (SELECT message_id FROM read_receipts WHERE user_id=?)
    """, (conversation_id, user_id, user_id)).fetchall()

    msg_ids = [r["id"] for r in unread_rows]
    with conn:
        for mid in msg_ids:
            conn.execute(
                "INSERT OR IGNORE INTO read_receipts(message_id, user_id, read_at) VALUES(?,?,?)",
                (mid, user_id, now),
            )
    conn.close()

    if msg_ids:
        import asyncio
        asyncio.create_task(manager.broadcast_to_conversation(conversation_id, {
            "type": "read_receipt",
            "conversation_id": conversation_id,
            "user_id": user_id,
            "message_ids": msg_ids,
        }))

    return {"marked": len(msg_ids)}

@router.post("/messages/{message_id}/reactions")
async def add_reaction(message_id: str, body: AddReaction, user_id: str = Depends(require_auth)):
    conn = get_connection()
    msg = conn.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
    if not msg:
        conn.close()
        raise HTTPException(status_code=404, detail="Message not found")

    member = conn.execute(
        "SELECT 1 FROM conversation_members WHERE conversation_id=? AND user_id=?",
        (msg["conversation_id"], user_id),
    ).fetchone()
    if not member:
        conn.close()
        raise HTTPException(status_code=403, detail="Not a member")

    reaction_id = str(uuid.uuid4())
    now = _now()
    try:
        with conn:
            conn.execute(
                "INSERT INTO reactions(id, message_id, user_id, emoji, created_at) VALUES(?,?,?,?,?)",
                (reaction_id, message_id, user_id, body.emoji, now),
            )
    except Exception:
        conn.close()
        raise HTTPException(status_code=409, detail="Reaction already exists")

    reaction = ReactionOut(id=reaction_id, message_id=message_id, user_id=user_id,
                           emoji=body.emoji, created_at=now)
    conn.close()

    import asyncio
    asyncio.create_task(manager.broadcast_to_conversation(msg["conversation_id"], {
        "type": "reaction_added",
        "reaction": reaction.model_dump(),
    }))

    return reaction

@router.post("/messages/{message_id}/preview")
async def set_message_preview(message_id: str, body: SetPreview, user_id: str = Depends(require_auth)):

    conn = get_connection()
    msg = conn.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
    if not msg:
        conn.close()
        raise HTTPException(status_code=404, detail="Message not found")

    conv_id = msg["conversation_id"]
    member = conn.execute(
        "SELECT 1 FROM conversation_members WHERE conversation_id=? AND user_id=?",
        (conv_id, user_id),
    ).fetchone()
    if not member:
        conn.close()
        raise HTTPException(status_code=403, detail="Not a member of this conversation")

    with conn:
        conn.execute(
            "UPDATE messages SET preview_title=?, preview_subtitle=? WHERE id=?",
            (body.title, body.subtitle, message_id),
        )

    msg_row = conn.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
    msg_out = _build_message_out(msg_row, conn)
    conn.close()

    import asyncio
    asyncio.create_task(manager.broadcast_to_conversation(conv_id, {
        "type": "message_preview",
        "message_id": message_id,
        "conversation_id": conv_id,
        "preview": {"title": body.title, "subtitle": body.subtitle},
    }))

    return msg_out

@router.delete("/messages/{message_id}/reactions/{emoji}")
async def remove_reaction(message_id: str, emoji: str, user_id: str = Depends(require_auth)):
    conn = get_connection()
    msg = conn.execute("SELECT * FROM messages WHERE id=?", (message_id,)).fetchone()
    if not msg:
        conn.close()
        raise HTTPException(status_code=404, detail="Message not found")

    member = conn.execute(
        "SELECT 1 FROM conversation_members WHERE conversation_id=? AND user_id=?",
        (msg["conversation_id"], user_id),
    ).fetchone()
    if not member:
        conn.close()
        raise HTTPException(status_code=403, detail="Not a member")

    with conn:
        conn.execute(
            "DELETE FROM reactions WHERE message_id=? AND user_id=? AND emoji=?",
            (message_id, user_id, emoji),
        )
    conn.close()

    import asyncio
    asyncio.create_task(manager.broadcast_to_conversation(msg["conversation_id"], {
        "type": "reaction_removed",
        "message_id": message_id,
        "user_id": user_id,
        "emoji": emoji,
    }))

    return {"removed": True}
