"""上传状态库（sqlite）—— D1 方案 A：RK3568 侧断点续传 + 幂等。

只有收到云端 accepted 才推进 units_sent；进程重启从 units_sent 续传，
不重发已确认的帧。云端契约不变（裸 INSERT），故"POST 成功但响应丢失"
窗口内的最多一个 batch 可能重复——可接受，离线可去重。

Python 3.8，仅标准库 sqlite3。
"""
from __future__ import annotations

import os
import sqlite3
import time
from typing import Optional

_SCHEMA = """
CREATE TABLE IF NOT EXISTS upload (
    file_path   TEXT PRIMARY KEY,
    kind        TEXT NOT NULL,
    session_id  TEXT NOT NULL,
    total_units INTEGER NOT NULL,
    units_sent  INTEGER NOT NULL DEFAULT 0,
    status      TEXT NOT NULL DEFAULT 'pending',  -- pending|uploading|done|error
    last_error  TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""


def _now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())


class StateDb:
    def __init__(self, path: str) -> None:
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        self._db = sqlite3.connect(path)
        self._db.row_factory = sqlite3.Row
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(_SCHEMA)
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def track(self, file_path: str, kind: str, session_id: str, total_units: int) -> None:
        """登记文件（已存在则只更新 total_units，不动 units_sent/status）。"""
        cur = self._db.execute("SELECT 1 FROM upload WHERE file_path=?", (file_path,))
        if cur.fetchone() is None:
            self._db.execute(
                "INSERT INTO upload(file_path,kind,session_id,total_units,units_sent,"
                "status,created_at,updated_at) VALUES(?,?,?,?,0,'pending',?,?)",
                (file_path, kind, session_id, total_units, _now(), _now()),
            )
        else:
            self._db.execute(
                "UPDATE upload SET total_units=?, updated_at=? WHERE file_path=?",
                (total_units, _now(), file_path),
            )
        self._db.commit()

    def next_pending(self) -> Optional[sqlite3.Row]:
        cur = self._db.execute(
            "SELECT * FROM upload WHERE status IN ('pending','uploading') "
            "ORDER BY created_at, file_path LIMIT 1"
        )
        return cur.fetchone()

    def set_progress(self, file_path: str, units_sent: int) -> None:
        self._db.execute(
            "UPDATE upload SET units_sent=?, status='uploading', last_error=NULL, "
            "updated_at=? WHERE file_path=?",
            (units_sent, _now(), file_path),
        )
        self._db.commit()

    def mark_done(self, file_path: str) -> None:
        self._db.execute(
            "UPDATE upload SET status='done', last_error=NULL, updated_at=? WHERE file_path=?",
            (_now(), file_path),
        )
        self._db.commit()

    def mark_error(self, file_path: str, msg: str) -> None:
        self._db.execute(
            "UPDATE upload SET status='error', last_error=?, updated_at=? WHERE file_path=?",
            (msg[:500], _now(), file_path),
        )
        self._db.commit()

    def reset_errors(self) -> None:
        """每轮开始把 error 复位为 pending 以便重试（不影响 done）。"""
        self._db.execute(
            "UPDATE upload SET status='pending', updated_at=? WHERE status='error'",
            (_now(),),
        )
        self._db.commit()

    def counts(self) -> dict:
        cur = self._db.execute(
            "SELECT status, COUNT(*) c FROM upload GROUP BY status"
        )
        out = {"pending": 0, "uploading": 0, "done": 0, "error": 0}
        for row in cur.fetchall():
            out[row["status"]] = row["c"]
        return out
