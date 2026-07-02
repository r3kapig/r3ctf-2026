import sqlite3
import os
from config import DB_PATH, DATA_DIR, ATTACHMENT_DIR

def get_connection() -> sqlite3.Connection:
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(ATTACHMENT_DIR, exist_ok=True)
    conn = get_connection()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id            TEXT PRIMARY KEY,
                handle        TEXT UNIQUE NOT NULL,
                display_name  TEXT NOT NULL,
                phone         TEXT UNIQUE NOT NULL,
                bio           TEXT DEFAULT '',
                avatar_seed   INTEGER DEFAULT 0,
                created_at    INTEGER NOT NULL,
                password_hash TEXT NOT NULL DEFAULT '',
                is_victim     INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token       TEXT PRIMARY KEY,
                user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                created_at  INTEGER NOT NULL,
                expires_at  INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id          TEXT PRIMARY KEY,
                pair_key    TEXT UNIQUE,
                created_at  INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS conversation_members (
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                PRIMARY KEY (conversation_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id              TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                sender_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                type            TEXT NOT NULL CHECK(type IN ('text','attachment')),
                body            TEXT,
                attachment_id   TEXT,
                reply_to_id     TEXT,
                created_at      INTEGER NOT NULL,
                preview_title   TEXT,
                preview_subtitle TEXT
            );

            CREATE TABLE IF NOT EXISTS attachments (
                id          TEXT PRIMARY KEY,
                uploader_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                filename    TEXT NOT NULL,
                mime_type   TEXT NOT NULL,
                kind        TEXT NOT NULL DEFAULT 'file',
                size        INTEGER NOT NULL,
                path        TEXT NOT NULL,
                created_at  INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reactions (
                id          TEXT PRIMARY KEY,
                message_id  TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                emoji       TEXT NOT NULL,
                created_at  INTEGER NOT NULL,
                UNIQUE(message_id, user_id, emoji)
            );

            CREATE TABLE IF NOT EXISTS read_receipts (
                message_id  TEXT NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
                user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                read_at     INTEGER NOT NULL,
                PRIMARY KEY (message_id, user_id)
            );

            CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, created_at);
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            CREATE INDEX IF NOT EXISTS idx_conv_members_user ON conversation_members(user_id);
        """)

        existing_users = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        if "password_hash" not in existing_users:
            conn.execute("ALTER TABLE users ADD COLUMN password_hash TEXT NOT NULL DEFAULT ''")
        if "is_victim" not in existing_users:
            conn.execute("ALTER TABLE users ADD COLUMN is_victim INTEGER NOT NULL DEFAULT 0")

        existing_msg = {row[1] for row in conn.execute("PRAGMA table_info(messages)").fetchall()}
        if "preview_title" not in existing_msg:
            conn.execute("ALTER TABLE messages ADD COLUMN preview_title TEXT")
        if "preview_subtitle" not in existing_msg:
            conn.execute("ALTER TABLE messages ADD COLUMN preview_subtitle TEXT")

        existing_conv = {row[1] for row in conn.execute("PRAGMA table_info(conversations)").fetchall()}
        if "pair_key" not in existing_conv:
            conn.execute("ALTER TABLE conversations ADD COLUMN pair_key TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_conversations_pair_key ON conversations(pair_key) WHERE pair_key IS NOT NULL")
    conn.close()

def reset_db() -> None:

    conn = get_connection()
    with conn:
        conn.executescript("""
            DELETE FROM read_receipts;
            DELETE FROM reactions;
            DELETE FROM messages;
            DELETE FROM attachments;
            DELETE FROM conversation_members;
            DELETE FROM conversations;
            DELETE FROM sessions;
            DELETE FROM users;
        """)
    conn.close()
    import shutil
    if os.path.isdir(ATTACHMENT_DIR):
        shutil.rmtree(ATTACHMENT_DIR)
    os.makedirs(ATTACHMENT_DIR, exist_ok=True)
