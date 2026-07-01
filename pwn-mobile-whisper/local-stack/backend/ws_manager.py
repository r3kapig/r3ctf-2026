import asyncio
import json
import time
from typing import Dict, Set
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):

        self._connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, user_id: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            if user_id not in self._connections:
                self._connections[user_id] = set()
            self._connections[user_id].add(ws)

    async def disconnect(self, user_id: str, ws: WebSocket) -> None:
        async with self._lock:
            if user_id in self._connections:
                self._connections[user_id].discard(ws)
                if not self._connections[user_id]:
                    del self._connections[user_id]

    def is_online(self, user_id: str) -> bool:
        return user_id in self._connections and len(self._connections[user_id]) > 0

    async def send_to_user(self, user_id: str, payload: dict) -> None:
        conns = list(self._connections.get(user_id, []))
        dead = []
        for ws in conns:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections.get(user_id, set()).discard(ws)

    async def broadcast_to_conversation(self, conversation_id: str, payload: dict) -> None:

        from database import get_connection
        conn = get_connection()
        rows = conn.execute(
            "SELECT user_id FROM conversation_members WHERE conversation_id=?",
            (conversation_id,),
        ).fetchall()
        conn.close()

        tasks = [self.send_to_user(row["user_id"], payload) for row in rows]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def broadcast_presence(self, user_id: str, online: bool) -> None:

        from database import get_connection
        conn = get_connection()
        rows = conn.execute("""
            SELECT DISTINCT cm2.user_id
            FROM conversation_members cm1
            JOIN conversation_members cm2 ON cm1.conversation_id = cm2.conversation_id
            WHERE cm1.user_id = ? AND cm2.user_id != ?
        """, (user_id, user_id)).fetchall()
        conn.close()

        payload = {
            "type": "presence",
            "user_id": user_id,
            "online": online,
            "timestamp": int(time.time()),
        }
        tasks = [self.send_to_user(row["user_id"], payload) for row in rows]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

manager = ConnectionManager()
