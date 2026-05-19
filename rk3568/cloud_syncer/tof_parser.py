"""解析 .tof 深度录制文件（与 nezha/qt_app/datarecorder 写入端严格一致）。

布局（全小端）：
  头   8B    "TOFREC1\\0"
  每帧 2062B seq(u32) ts_ms(u64) valid_count(u16) depths(1024*u16 = 2048B)

末尾不足一帧的残留字节忽略（采集中途文件）。Python 3.8，仅标准库。
"""
from __future__ import annotations

import os
import struct
from typing import Iterator, NamedTuple

TOF_MAGIC = b"TOFREC1\x00"
HEADER_SIZE = 8
DEPTHS_SIZE = 2048
RECORD_SIZE = 2062  # 4 + 8 + 2 + 2048
_HEAD = struct.Struct("<IQH")  # seq, ts_ms, valid_count


class BadTofFile(Exception):
    """文件头非法或损坏，调用方应隔离该文件。"""


class TofFrame(NamedTuple):
    seq: int
    ts_ms: int
    valid_count: int
    depths: bytes  # 2048 字节，直接 base64 上传


def count_frames(path: str) -> int:
    """返回完整帧数（忽略末尾残帧）。不校验头，调用方先 validate。"""
    size = os.path.getsize(path)
    if size < HEADER_SIZE:
        return 0
    return (size - HEADER_SIZE) // RECORD_SIZE


def validate_header(path: str) -> None:
    with open(path, "rb") as f:
        magic = f.read(HEADER_SIZE)
    if magic != TOF_MAGIC:
        raise BadTofFile("bad magic %r in %s" % (magic, path))


def iter_frames(path: str, start: int = 0) -> Iterator[TofFrame]:
    """从第 start 帧（0 基）起迭代完整帧。头非法抛 BadTofFile。"""
    with open(path, "rb") as f:
        magic = f.read(HEADER_SIZE)
        if magic != TOF_MAGIC:
            raise BadTofFile("bad magic %r in %s" % (magic, path))
        f.seek(HEADER_SIZE + start * RECORD_SIZE)
        while True:
            rec = f.read(RECORD_SIZE)
            if len(rec) < RECORD_SIZE:
                return  # 末尾残帧，停止
            seq, ts_ms, valid = _HEAD.unpack_from(rec, 0)
            depths = rec[12:12 + DEPTHS_SIZE]
            yield TofFrame(seq, ts_ms, valid, depths)
