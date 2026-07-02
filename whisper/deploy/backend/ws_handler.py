import json
import time
import asyncio

from fastapi import WebSocket, WebSocketDisconnect, Query
from auth import get_user_id_from_token
from ws_manager import manager
from database import get_connection

async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    user_id = get_user_id_from_token(token)
    if user_id is None:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await manager.connect(user_id, websocket)

    asyncio.create_task(manager.broadcast_presence(user_id, online=True))

    try:
        await websocket.send_json({
            "type": "connected",
            "user_id": user_id,
            "timestamp": int(time.time()),
        })

        while True:
            try:
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            except asyncio.TimeoutError:
                try:
                    await websocket.send_json({"type": "ping", "timestamp": int(time.time())})
                except Exception:
                    break
                continue

            try:
                frame = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "code": "bad_json", "message": "Invalid JSON"})
                continue

            ftype = frame.get("type")

            if ftype == "ping":
                await websocket.send_json({"type": "pong", "timestamp": int(time.time())})

            elif ftype == "typing":
                conv_id = frame.get("conversation_id")
                if conv_id:
                    conn = get_connection()
                    member = conn.execute(
                        "SELECT 1 FROM conversation_members WHERE conversation_id=? AND user_id=?",
                        (conv_id, user_id),
                    ).fetchone()
                    conn.close()
                    if member:
                        asyncio.create_task(manager.broadcast_to_conversation(conv_id, {
                            "type": "typing",
                            "conversation_id": conv_id,
                            "user_id": user_id,
                            "timestamp": int(time.time()),
                        }))

            elif ftype == "stop_typing":
                conv_id = frame.get("conversation_id")
                if conv_id:
                    conn = get_connection()
                    member = conn.execute(
                        "SELECT 1 FROM conversation_members WHERE conversation_id=? AND user_id=?",
                        (conv_id, user_id),
                    ).fetchone()
                    conn.close()
                    if member:
                        asyncio.create_task(manager.broadcast_to_conversation(conv_id, {
                            "type": "stop_typing",
                            "conversation_id": conv_id,
                            "user_id": user_id,
                            "timestamp": int(time.time()),
                        }))

            elif ftype == "mark_read":
                conv_id = frame.get("conversation_id")
                msg_ids = frame.get("message_ids", [])
                if conv_id and msg_ids:
                    now = int(time.time())
                    conn = get_connection()
                    member = conn.execute(
                        "SELECT 1 FROM conversation_members WHERE conversation_id=? AND user_id=?",
                        (conv_id, user_id),
                    ).fetchone()
                    if member:
                        with conn:
                            for mid in msg_ids:
                                conn.execute(
                                    "INSERT OR IGNORE INTO read_receipts(message_id, user_id, read_at) VALUES(?,?,?)",
                                    (mid, user_id, now),
                                )
                        conn.close()
                        asyncio.create_task(manager.broadcast_to_conversation(conv_id, {
                            "type": "read_receipt",
                            "conversation_id": conv_id,
                            "user_id": user_id,
                            "message_ids": msg_ids,
                        }))
                    else:
                        conn.close()

            else:
                await websocket.send_json({
                    "type": "error",
                    "code": "unknown_frame_type",
                    "message": f"Unknown frame type: {ftype}",
                })

    except WebSocketDisconnect:
        pass
    finally:
        await manager.disconnect(user_id, websocket)
        asyncio.create_task(manager.broadcast_presence(user_id, online=False))
