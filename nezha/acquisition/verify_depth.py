#!/usr/bin/env python3
"""Verify a TOF v1 depth.dat frame."""

import os
import struct
import sys
import time

TOF_FRAME_SIZE = 2070
TOF_MAGIC = 0x50464F54
TOF_VERSION = 1
TOF_HDR_SIZE = 16
MAX_DEPTH_MM = 8450
WIDTH = 32
HEIGHT = 32
PIXELS = WIDTH * HEIGHT


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if (crc & 1) else (crc >> 1)
    return crc & 0xFFFF


def parse_frame(path: str) -> dict:
    stat = os.stat(path)
    if stat.st_size != TOF_FRAME_SIZE:
        raise ValueError(f"[FAIL] file size {stat.st_size} != {TOF_FRAME_SIZE}")

    with open(path, "rb") as f:
        buf = f.read(TOF_FRAME_SIZE)

    magic, version, hdr_sz, flags, seq, width, height, valid_count, reserved = (
        struct.unpack_from("<IBBHIHHHH", buf, 0)
    )
    if magic != TOF_MAGIC:
        raise ValueError(f"[FAIL] magic 0x{magic:08X} != 0x{TOF_MAGIC:08X}")
    if version != TOF_VERSION:
        raise ValueError(f"[FAIL] version {version} != {TOF_VERSION}")
    if hdr_sz != TOF_HDR_SIZE:
        raise ValueError(f"[FAIL] headerSize {hdr_sz} != {TOF_HDR_SIZE}")
    if flags != 0 or reserved != 0:
        raise ValueError(f"[FAIL] flags/reserved must be 0, got flags={flags} reserved={reserved}")
    if width != WIDTH or height != HEIGHT:
        raise ValueError(f"[FAIL] dimensions {width}x{height} != {WIDTH}x{HEIGHT}")

    calc_crc = crc16_modbus(buf[4:2068])
    file_crc = struct.unpack_from("<H", buf, 2068)[0]
    if calc_crc != file_crc:
        raise ValueError(f"[FAIL] CRC mismatch calc=0x{calc_crc:04X} file=0x{file_crc:04X}")

    depths = list(struct.unpack_from("<1024H", buf, 20))

    out_of_range = [(i, d) for i, d in enumerate(depths) if d > MAX_DEPTH_MM]
    if out_of_range:
        i, d = out_of_range[0]
        raise ValueError(f"[FAIL] {len(out_of_range)} depths exceed {MAX_DEPTH_MM}mm, first idx={i} d={d}")

    actual_valid = sum(1 for d in depths if d > 0)
    if valid_count != actual_valid:
        raise ValueError(f"[FAIL] validCount={valid_count} but actual non-zero pixels={actual_valid}")

    return {"seq": seq, "validCount": valid_count, "depths": depths}


def check_scene(depths: list) -> list:
    warnings = []
    center_depths = []
    for row in range(HEIGHT // 2 - 1, HEIGHT // 2 + 2):
        for col in range(WIDTH // 2 - 1, WIDTH // 2 + 2):
            d = depths[row * WIDTH + col]
            if d > 0:
                center_depths.append(d)

    edge_depths = []
    for col in range(WIDTH):
        for row in [0, HEIGHT - 1]:
            d = depths[row * WIDTH + col]
            if d > 0:
                edge_depths.append(d)

    if center_depths and edge_depths:
        avg_center = sum(center_depths) / len(center_depths)
        avg_edge = sum(edge_depths) / len(edge_depths)
        if avg_center >= avg_edge:
            warnings.append(
                f"[WARN] center average {avg_center:.0f}mm >= edge average {avg_edge:.0f}mm"
            )
        else:
            print(f"  [7] scene check center={avg_center:.0f}mm edge={avg_edge:.0f}mm OK")
    else:
        warnings.append("[WARN] insufficient valid pixels for scene check")

    return warnings


def verify_once(path: str, prev_seq: int = -1) -> int:
    print("\n" + "-" * 52)
    print(f"  file: {path}")
    try:
        frame = parse_frame(path)
    except ValueError as e:
        print(e)
        return prev_seq

    seq = frame["seq"]
    depths = frame["depths"]

    print(f"  [1] file size   {TOF_FRAME_SIZE} bytes OK")
    print(f"  [2] magic       0x{TOF_MAGIC:08X} ('TOFP') OK")
    print("  [3] CRC16       OK")
    print(f"  [4] seq         {seq}", end="")
    if prev_seq >= 0:
        if seq == prev_seq + 1:
            print(" monotonic OK")
        elif seq == prev_seq:
            print(" unchanged")
        else:
            print(f" [WARN] skipped from previous seq {prev_seq}")
    else:
        print()
    print(f"  [5] depths      range [0,{MAX_DEPTH_MM}] mm OK")
    print(f"  [6] validCount  {frame['validCount']}/{PIXELS} OK")

    warnings = check_scene(depths)
    for warning in warnings:
        print(f"  {warning}")

    row_avgs = []
    for row in range(HEIGHT):
        row_depths = [depths[row * WIDTH + col] for col in range(WIDTH) if depths[row * WIDTH + col] > 0]
        row_avgs.append(sum(row_depths) / len(row_depths) if row_depths else 0)
    min_row = min(range(HEIGHT), key=lambda r: row_avgs[r] if row_avgs[r] > 0 else 9999)
    print(f"\n  depth summary: nearest row={min_row} avg={row_avgs[min_row]:.0f}mm max-row-avg={max(row_avgs):.0f}mm")
    print("  PASS" if not warnings else "  PASS with warnings")
    return seq


def main() -> None:
    args = sys.argv[1:]
    watch = "--watch" in args
    args = [arg for arg in args if arg != "--watch"]
    path = args[0] if args else "/tmp/depth.dat"

    if not watch:
        verify_once(path)
        return

    print(f"[watch mode] monitoring {path}, Ctrl-C to exit")
    prev_seq = -1
    prev_mtime = -1
    try:
        while True:
            try:
                mtime = os.stat(path).st_mtime
            except FileNotFoundError:
                time.sleep(0.2)
                continue
            if mtime != prev_mtime:
                prev_mtime = mtime
                prev_seq = verify_once(path, prev_seq)
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n[watch] stopped")


if __name__ == "__main__":
    main()
