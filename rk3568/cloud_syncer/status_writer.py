"""把上传进度原子写到状态文件，供 spi_receiver 在收到哪吒 CMD=0x01 时
读取并组 CMD=0x05 回报（cloud_syncer 不直接碰 USB-SPI 设备，解耦）。

Python 3.8，仅标准库。
"""
from __future__ import annotations

import json
import os
import time
from typing import Optional


def write_status(path: str, online: bool, counts: dict,
                  current_file: Optional[str], units_sent: int,
                  total_units: int, last_error: Optional[str]) -> None:
    payload = {
        "online": online,
        "counts": counts,                       # {pending,uploading,done,error}
        "current_file": current_file,
        "units_sent": units_sent,
        "total_units": total_units,
        "last_error": last_error,
        "ts": int(time.time()),
    }
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    os.replace(tmp, path)  # 原子替换
