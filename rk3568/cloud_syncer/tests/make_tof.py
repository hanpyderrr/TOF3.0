"""合成 .tof 测试文件（格式与 nezha datarecorder 一致）。

CLI: python3 make_tof.py <out.tof> <n_frames> [start_seq] [--bad]
"""
from __future__ import annotations

import struct
import sys

TOF_MAGIC = b"TOFREC1\x00"
_HEAD = struct.Struct("<IQH")


def write_tof(path: str, n: int, start_seq: int = 0, bad: bool = False) -> None:
    with open(path, "wb") as f:
        f.write(b"BADMAGIC" if bad else TOF_MAGIC)
        for i in range(n):
            seq = start_seq + i
            ts_ms = 1_700_000_000_000 + i
            valid = (seq * 7) % 1024
            f.write(_HEAD.pack(seq, ts_ms, valid))
            # 2048B depths：用 seq 填充，便于校验
            f.write(bytes(((seq + j) & 0xFF) for j in range(2048)))


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--bad"]
    is_bad = "--bad" in sys.argv
    out = args[0]
    n = int(args[1])
    start = int(args[2]) if len(args) > 2 else 0
    write_tof(out, n, start, is_bad)
    print("wrote %s frames=%d start=%d bad=%s" % (out, n, start, is_bad))
