import sqlite3
import os

DB_PATH = os.getenv("DB_PATH", "/data/bot.db")


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username    TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS servers (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id     INTEGER NOT NULL,
            name            TEXT NOT NULL,
            host            TEXT NOT NULL,
            port            INTEGER NOT NULL DEFAULT 27015,
            rcon_password   TEXT NOT NULL,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        );
    """)
    conn.commit()
    conn.close()


def ensure_user(telegram_id: int, username: str | None = None):
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO users (telegram_id, username) VALUES (?, ?)",
        (telegram_id, username),
    )
    if username:
        conn.execute(
            "UPDATE users SET username = ? WHERE telegram_id = ?",
            (username, telegram_id),
        )
    conn.commit()
    conn.close()


def add_server(telegram_id: int, name: str, host: str, port: int, rcon_password: str) -> int:
    conn = _connect()
    cur = conn.execute(
        "INSERT INTO servers (telegram_id, name, host, port, rcon_password) VALUES (?, ?, ?, ?, ?)",
        (telegram_id, name, host, port, rcon_password),
    )
    server_id = cur.lastrowid
    conn.commit()
    conn.close()
    return server_id


def get_user_servers(telegram_id: int) -> list[dict]:
    conn = _connect()
    rows = conn.execute(
        "SELECT * FROM servers WHERE telegram_id = ? ORDER BY created_at", (telegram_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_server(server_id: int, telegram_id: int) -> dict | None:
    conn = _connect()
    row = conn.execute(
        "SELECT * FROM servers WHERE id = ? AND telegram_id = ?",
        (server_id, telegram_id),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_server(server_id: int, telegram_id: int):
    conn = _connect()
    conn.execute(
        "DELETE FROM servers WHERE id = ? AND telegram_id = ?",
        (server_id, telegram_id),
    )
    conn.commit()
    conn.close()


def update_server(server_id: int, telegram_id: int, **kwargs):
    allowed = {"name", "host", "port", "rcon_password"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    set_clause = ", ".join(f"{k} = ?" for k in fields)
    values = list(fields.values()) + [server_id, telegram_id]
    conn = _connect()
    conn.execute(
        f"UPDATE servers SET {set_clause} WHERE id = ? AND telegram_id = ?", values
    )
    conn.commit()
    conn.close()
