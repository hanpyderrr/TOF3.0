"""扫描 ~/tof-buffer/ 选出"完整"的 .tof 文件。

约定：spi_receiver 重组时写 name.tof.part，完成后原子 rename 为 name.tof。
故只处理无 .part 后缀、且不在 .bad/ 隔离区的 .tof，按 mtime 升序（FIFO）。

session_id = 文件名去扩展名（与哪吒 CloudSyncer 的 completeBaseName 约定一致）。
Python 3.8，仅标准库。
"""
from __future__ import annotations

import os
from typing import List, Tuple

BAD_DIR = ".bad"


def session_id_of(file_path: str) -> str:
    return os.path.splitext(os.path.basename(file_path))[0]


def find_tof_files(buffer_dir: str) -> List[str]:
    found = []  # type: List[Tuple[float, str]]
    for root, dirs, files in os.walk(buffer_dir):
        # 跳过隔离区
        dirs[:] = [d for d in dirs if d != BAD_DIR]
        for name in files:
            if not name.endswith(".tof"):
                continue
            path = os.path.join(root, name)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            found.append((mtime, path))
    found.sort(key=lambda t: (t[0], t[1]))
    return [p for _, p in found]


def quarantine(buffer_dir: str, file_path: str) -> str:
    """把坏文件移到 buffer_dir/.bad/，返回新路径。"""
    bad_dir = os.path.join(buffer_dir, BAD_DIR)
    os.makedirs(bad_dir, exist_ok=True)
    dst = os.path.join(bad_dir, os.path.basename(file_path))
    # 同名冲突则追加计数
    base, ext = os.path.splitext(dst)
    i = 1
    while os.path.exists(dst):
        dst = "%s.%d%s" % (base, i, ext)
        i += 1
    os.replace(file_path, dst)
    return dst
