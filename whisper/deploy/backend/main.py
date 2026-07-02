import sys
import os
from contextlib import asynccontextmanager

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, WebSocket, Query
from fastapi.middleware.cors import CORSMiddleware

from database import init_db
from routers.auth_router import router as auth_router
from routers.users_router import router as users_router
from routers.conversations_router import router as conv_router
from routers.attachments_router import router as att_router
from routers.admin_router import router as admin_router
from ws_handler import websocket_endpoint

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(
    title="Whisper",
    description="Private messaging backend.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(conv_router)
app.include_router(att_router)
app.include_router(admin_router)

@app.websocket("/ws")
async def ws_route(websocket: WebSocket, token: str = Query(...)):
    await websocket_endpoint(websocket, token)

@app.get("/health")
async def health():
    return {"status": "ok", "service": "whisper-backend"}

if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
