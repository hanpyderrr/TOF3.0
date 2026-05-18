import base64
import binascii
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

from models import init_db


DB_PATH = Path("data") / "tof.db"


class DepthFrame(BaseModel):
    seq: int
    ts_ms: int
    valid_count: int
    depths_b64: str


class DepthFrameRequest(BaseModel):
    session_id: str
    frames: list[DepthFrame]


@asynccontextmanager
async def lifespan(app: FastAPI):
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    await init_db(str(DB_PATH))
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/frames/depth")
async def post_depth_frames(payload: DepthFrameRequest) -> dict[str, int]:
    rows = []
    for frame in payload.frames:
        try:
            depths_blob = base64.b64decode(frame.depths_b64, validate=True)
        except (binascii.Error, ValueError) as exc:
            raise HTTPException(status_code=400, detail="Invalid depths_b64") from exc

        if len(depths_blob) != 2048:
            raise HTTPException(status_code=400, detail="depths_b64 must decode to 2048 bytes")

        rows.append(
            (
                payload.session_id,
                frame.seq,
                frame.ts_ms,
                frame.valid_count,
                depths_blob,
            )
        )

    async with aiosqlite.connect(str(DB_PATH)) as db:
        await db.executemany(
            """
            INSERT INTO frames (session_id, seq, ts_ms, valid_count, depths_blob)
            VALUES (?, ?, ?, ?, ?)
            """,
            rows,
        )
        await db.commit()

    return {"accepted": len(rows)}


@app.get("/api/sessions")
async def get_sessions() -> list[dict[str, int | str]]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT
                session_id,
                COUNT(*) AS frame_count,
                MIN(ts_ms) AS first_ts,
                MAX(ts_ms) AS last_ts
            FROM frames
            GROUP BY session_id
            ORDER BY session_id
            """
        )
        rows = await cursor.fetchall()

    return [dict(row) for row in rows]


@app.get("/api/sessions/{session_id}/frames")
async def get_session_frames(
    session_id: str,
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
) -> list[dict[str, int | str]]:
    async with aiosqlite.connect(str(DB_PATH)) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT seq, ts_ms, valid_count, depths_blob
            FROM frames
            WHERE session_id = ?
            ORDER BY seq
            LIMIT ? OFFSET ?
            """,
            (session_id, limit, offset),
        )
        rows = await cursor.fetchall()

    return [
        {
            "seq": row["seq"],
            "ts_ms": row["ts_ms"],
            "valid_count": row["valid_count"],
            "depths_b64": base64.b64encode(row["depths_blob"]).decode("ascii"),
        }
        for row in rows
    ]
