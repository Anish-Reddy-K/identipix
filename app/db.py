import sqlite3
import time
from contextlib import contextmanager

import numpy as np

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS events(
  id TEXT PRIMARY KEY,
  admin_token TEXT NOT NULL,
  folder_id TEXT NOT NULL,
  name TEXT,
  status TEXT NOT NULL,
  error TEXT,
  done INTEGER DEFAULT 0,
  total INTEGER DEFAULT 0,
  last_sync INTEGER,
  created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS photos(
  event_id TEXT, file_id TEXT, name TEXT,
  PRIMARY KEY(event_id, file_id)
);
CREATE TABLE IF NOT EXISTS faces(
  event_id TEXT, file_id TEXT,
  emb BLOB NOT NULL
);
CREATE INDEX IF NOT EXISTS faces_event ON faces(event_id);
"""


@contextmanager
def conn():
    """Commit on success, roll back on error, always close."""
    c = sqlite3.connect(config.DATA_DIR / "identipix.db", timeout=30)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    try:
        with c:
            yield c
    finally:
        c.close()


def init() -> None:
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with conn() as c:
        c.executescript(SCHEMA)


def create_event(id: str, admin_token: str, folder_id: str, name: str | None) -> None:
    with conn() as c:
        c.execute(
            "INSERT INTO events(id, admin_token, folder_id, name, status, created_at) "
            "VALUES(?,?,?,?, 'indexing', ?)",
            (id, admin_token, folder_id, name, int(time.time())),
        )


def get_event(id: str):
    with conn() as c:
        return c.execute("SELECT * FROM events WHERE id=?", (id,)).fetchone()


def update_event(id: str, **fields) -> None:
    cols = ", ".join(f"{k}=?" for k in fields)
    with conn() as c:
        c.execute(f"UPDATE events SET {cols} WHERE id=?", (*fields.values(), id))


def indexing_event_ids() -> list[str]:
    with conn() as c:
        return [r["id"] for r in c.execute("SELECT id FROM events WHERE status='indexing'")]


def processed_file_ids(event_id: str) -> set[str]:
    with conn() as c:
        return {r["file_id"] for r in c.execute("SELECT file_id FROM photos WHERE event_id=?", (event_id,))}


def record_photo(event_id: str, file_id: str, name: str, embs: list[np.ndarray]) -> None:
    """One transaction: photo row + face rows + progress. Skipped if event was deleted."""
    with conn() as c:
        if c.execute("UPDATE events SET done=done+1 WHERE id=?", (event_id,)).rowcount == 0:
            return
        c.execute("INSERT OR IGNORE INTO photos(event_id, file_id, name) VALUES(?,?,?)", (event_id, file_id, name))
        c.executemany(
            "INSERT INTO faces(event_id, file_id, emb) VALUES(?,?,?)",
            [(event_id, file_id, e.astype(np.float32).tobytes()) for e in embs],
        )


def face_count(event_id: str) -> int:
    with conn() as c:
        return c.execute("SELECT COUNT(*) FROM faces WHERE event_id=?", (event_id,)).fetchone()[0]


def load_faces(event_id: str) -> tuple[np.ndarray, list[str]]:
    with conn() as c:
        rows = c.execute("SELECT file_id, emb FROM faces WHERE event_id=?", (event_id,)).fetchall()
    if not rows:
        return np.zeros((0, 128), np.float32), []
    mat = np.vstack([np.frombuffer(r["emb"], dtype=np.float32) for r in rows])
    return mat, [r["file_id"] for r in rows]


def photo_names(event_id: str, file_ids: list[str]) -> dict[str, str]:
    if not file_ids:
        return {}
    q = ",".join("?" * len(file_ids))
    with conn() as c:
        rows = c.execute(f"SELECT file_id, name FROM photos WHERE event_id=? AND file_id IN ({q})", (event_id, *file_ids))
        return {r["file_id"]: r["name"] for r in rows}


def delete_event(id: str) -> None:
    with conn() as c:
        for t in ("faces", "photos"):
            c.execute(f"DELETE FROM {t} WHERE event_id=?", (id,))
        c.execute("DELETE FROM events WHERE id=?", (id,))


def expired_event_ids(cutoff: int) -> list[str]:
    with conn() as c:
        return [r["id"] for r in c.execute("SELECT id FROM events WHERE created_at < ?", (cutoff,))]
