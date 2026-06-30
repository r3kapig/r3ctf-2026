import os

CTF_MODE: bool = os.getenv("WHISPER_CTF_MODE", "1") == "1"
TOKEN_TTL: int = int(os.getenv("WHISPER_TOKEN_TTL", "86400"))
DATA_DIR: str = os.getenv("WHISPER_DATA_DIR", "./data")
ADMIN_TOKEN: str = os.getenv("WHISPER_ADMIN_TOKEN", "ctf-admin-token")
HOST: str = os.getenv("WHISPER_HOST", "0.0.0.0")
PORT: int = int(os.getenv("WHISPER_PORT", "8000"))
DB_PATH: str = os.getenv("WHISPER_DB_PATH", os.path.join(DATA_DIR, "whisper.db"))
ATTACHMENT_DIR: str = os.path.join(DATA_DIR, "attachments")
