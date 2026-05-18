import aiosqlite


CREATE_SQL = """
CREATE TABLE IF NOT EXISTS frames (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, seq INTEGER NOT NULL, ts_ms INTEGER NOT NULL, valid_count INTEGER NOT NULL, depths_blob BLOB NOT NULL, created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE INDEX IF NOT EXISTS idx_session ON frames(session_id, seq);
"""


async def init_db(db_path: str) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.executescript(CREATE_SQL)
        await db.commit()
