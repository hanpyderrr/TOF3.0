"""cloud_syncer 离线端到端测试（无需 RK3568 / 5G / FastAPI）。

场景：
  1 happy   137 帧全部上传，文件删除，db done
  2 resume  传到一半模拟断网，重启后续传，无重复、不丢帧
  3 badfile 坏 magic 文件被隔离到 .bad/，不上传

运行：python3 tests/test_e2e.py   （退出码 0 = 全过）
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
sys.path.insert(0, PKG)   # cloud_syncer 模块目录
sys.path.insert(0, HERE)  # mock_cloud / make_tof

import cloud_syncer  # noqa: E402
from config import parse_config  # noqa: E402
from make_tof import write_tof  # noqa: E402
from mock_cloud import MockCloud  # noqa: E402
from state_db import StateDb  # noqa: E402

logging.basicConfig(level=logging.WARNING,
                    format="%(levelname)s %(message)s")

_failures = []


def check(cond: bool, msg: str) -> None:
    status = "PASS" if cond else "FAIL"
    print("  [%s] %s" % (status, msg))
    if not cond:
        _failures.append(msg)


def _cfg(url: str, work: str, batch: int = 25):
    return parse_config([
        "--cloud-url", url,
        "--buffer-dir", os.path.join(work, "buf"),
        "--state-db", os.path.join(work, "state.db"),
        "--status-file", os.path.join(work, "status.json"),
        "--depth-batch", str(batch),
        "--max-retry", "1",
        "--http-timeout", "5",
    ])


def scenario_happy(cloud: MockCloud) -> None:
    print("场景1 happy（137 帧全量上传）")
    cloud.reset()
    work = tempfile.mkdtemp()
    try:
        buf = os.path.join(work, "buf")
        os.makedirs(buf)
        tof = os.path.join(buf, "20260519_101010.tof")
        write_tof(tof, 137)
        cfg = _cfg(cloud.base_url, work)
        db = StateDb(cfg.state_db)
        cloud_syncer.sync_pass(cfg, db)

        seqs = sorted(s for _, s in cloud.received)
        check(seqs == list(range(137)), "云端收到 137 帧且 seq 连续 0..136")
        check(len(cloud.received) == 137, "无重复（收到行数==137）")
        check(not os.path.exists(tof), "本地文件上传后已删除")
        check(db.counts().get("done") == 1, "状态库标记 done=1")
        check(os.path.exists(cfg.status_file), "状态文件已写出")
        db.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def scenario_resume(cloud: MockCloud) -> None:
    print("场景2 resume（断网中断后续传，无重复/不丢帧）")
    cloud.reset()
    work = tempfile.mkdtemp()
    try:
        buf = os.path.join(work, "buf")
        os.makedirs(buf)
        tof = os.path.join(buf, "20260519_202020.tof")
        write_tof(tof, 100)
        cfg = _cfg(cloud.base_url, work, batch=25)
        db = StateDb(cfg.state_db)

        cloud.set_fail_after(2)  # 前 2 个 batch 成功，第 3 个起 503
        cloud_syncer.sync_pass(cfg, db)
        mid = len(cloud.received)
        check(mid == 50, "中断时云端已确认 50 帧（实得 %d）" % mid)
        check(os.path.exists(tof), "中断后本地文件保留（未删）")

        cloud.set_fail_after(None)  # 网络恢复
        cloud_syncer.sync_pass(cfg, db)

        seqs = sorted(s for _, s in cloud.received)
        check(len(cloud.received) == 100, "续传后总行数==100（无重复，实得 %d）"
              % len(cloud.received))
        check(seqs == list(range(100)), "seq 完整 0..99，不丢帧")
        check(not os.path.exists(tof), "续传完成后本地文件删除")
        check(db.counts().get("done") == 1, "状态库标记 done=1")
        db.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def scenario_badfile(cloud: MockCloud) -> None:
    print("场景3 badfile（坏 magic 隔离）")
    cloud.reset()
    work = tempfile.mkdtemp()
    try:
        buf = os.path.join(work, "buf")
        os.makedirs(buf)
        tof = os.path.join(buf, "20260519_303030.tof")
        write_tof(tof, 10, bad=True)
        before = len(cloud.received)
        cfg = _cfg(cloud.base_url, work)
        db = StateDb(cfg.state_db)
        cloud_syncer.sync_pass(cfg, db)

        check(not os.path.exists(tof), "坏文件已移出原位")
        bad_dir = os.path.join(buf, ".bad")
        moved = os.path.isdir(bad_dir) and len(os.listdir(bad_dir)) == 1
        check(moved, "坏文件被隔离到 .bad/")
        check(len(cloud.received) == before, "坏文件未产生任何上传")
        db.close()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main() -> int:
    cloud = MockCloud()
    cloud.start()
    try:
        scenario_happy(cloud)
        scenario_resume(cloud)
        scenario_badfile(cloud)
    finally:
        cloud.stop()

    print("\n%s" % ("全部通过 ✅" if not _failures
                     else "失败 %d 项 ❌: %s" % (len(_failures), _failures)))
    return 0 if not _failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
