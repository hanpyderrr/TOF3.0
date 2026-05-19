#!/usr/bin/env python3
"""cloud_syncer 守护进程：扫描 ~/tof-buffer/ 的 .tof 深度文件，5G 在线时
POST 到云端 FastAPI /api/frames/depth，成功后删本地并把进度写状态文件。

D1=A：本地状态库断点续传；TCSPC 本轮不做。
失败不阻塞、不退出；进程级 SIGTERM/SIGINT 干净退出。
Python 3.8，仅标准库。

用法见 `python3 cloud_syncer.py --help`，部署见 docs/cloud_syncer_plan.md。
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import signal
import time
from typing import Iterator, List, Optional

from buffer_scanner import find_tof_files, quarantine, session_id_of
from config import Config, parse_config
from state_db import StateDb
from status_writer import write_status
from tof_parser import (
    BadTofFile,
    TofFrame,
    count_frames,
    iter_frames,
    validate_header,
)
from uploader import FatalError, RetryableError, health_ok, post_depth

log = logging.getLogger("cloud_syncer")

_stop = False


def _on_signal(signum, frame):  # noqa: ARG001
    global _stop
    _stop = True
    log.info("收到信号 %d，准备干净退出", signum)


def _setup_logging(cfg: Config) -> None:
    level = getattr(logging, cfg.log_level, logging.INFO)
    logging.basicConfig(level=level,
                        format="%(asctime)s %(levelname)s %(message)s")
    if cfg.log_file:
        d = os.path.dirname(cfg.log_file)
        if d:
            os.makedirs(d, exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            cfg.log_file, maxBytes=5 * 1024 * 1024, backupCount=3)
        fh.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(message)s"))
        logging.getLogger().addHandler(fh)


def _batched(it: Iterator[TofFrame], n: int) -> Iterator[List[TofFrame]]:
    batch = []  # type: List[TofFrame]
    for fr in it:
        batch.append(fr)
        if len(batch) >= n:
            yield batch
            batch = []
    if batch:
        yield batch


def _process_file(cfg: Config, db: StateDb, row) -> bool:
    """处理一个文件。返回 True=本文件已 done，False=遇可重试错误（保留重试）。
    坏文件（FatalError/BadTofFile）隔离后视为已处理（True）。"""
    path = row["file_path"]
    session = row["session_id"]

    if not os.path.exists(path):
        db.mark_error(path, "file disappeared")
        log.warning("文件消失，跳过: %s", path)
        return True

    try:
        total = count_frames(path)
    except OSError as e:
        db.mark_error(path, "stat failed: %s" % e)
        return False

    db.track(path, "tof", session, total)
    start = row["units_sent"]

    if total == 0:
        log.info("空文件，标记完成: %s", path)
        db.mark_done(path)
        _finalize(cfg, path)
        return True

    if start >= total:
        db.mark_done(path)
        _finalize(cfg, path)
        return True

    log.info("上传 %s session=%s 帧 %d/%d", path, session, start, total)
    sent = start
    try:
        for batch in _batched(iter_frames(path, start), cfg.depth_batch):
            if _stop:
                log.info("停止信号，暂停于 %d/%d", sent, total)
                return False
            accepted = _post_with_retry(cfg, session, batch)
            if accepted != len(batch):
                log.warning("accepted=%d 与 batch=%d 不符，按 accepted 推进",
                            accepted, len(batch))
            sent += accepted
            db.set_progress(path, sent)
            _write_status(cfg, db, path, sent, total, None)
            if accepted != len(batch):
                # 保守：本轮停止，下轮从 sent 续传剩余
                return False
    except BadTofFile as e:
        dst = quarantine(cfg.buffer_dir, path)
        db.mark_error(path, "bad tof, quarantined -> %s (%s)" % (dst, e))
        log.error("坏 .tof 文件已隔离: %s -> %s", path, dst)
        return True
    except FatalError as e:
        dst = quarantine(cfg.buffer_dir, path)
        db.mark_error(path, "fatal upload (4xx), quarantined -> %s (%s)" % (dst, e))
        log.error("4xx 坏数据，文件已隔离: %s -> %s", path, dst)
        return True
    except RetryableError as e:
        db.mark_error(path, "retryable: %s" % e)
        log.warning("可重试错误，保留待重试 %s : %s", path, e)
        return False

    if sent >= total:
        db.mark_done(path)
        _finalize(cfg, path)
        log.info("完成上传: %s (%d 帧)", path, total)
        return True
    return False


def _post_with_retry(cfg: Config, session: str, batch: List[TofFrame]) -> int:
    delay = 1.0
    last = None  # type: Optional[Exception]
    for attempt in range(1, cfg.max_retry + 1):
        try:
            return post_depth(cfg.cloud_url, session, batch, cfg.http_timeout)
        except RetryableError as e:
            last = e
            log.warning("上传重试 %d/%d: %s", attempt, cfg.max_retry, e)
            if attempt < cfg.max_retry and not _stop:
                time.sleep(min(delay, 30.0))
                delay *= 2
    raise RetryableError("重试 %d 次仍失败: %s" % (cfg.max_retry, last))


def _finalize(cfg: Config, path: str) -> None:
    if cfg.delete_after_upload:
        try:
            os.remove(path)
        except OSError as e:
            log.warning("删除已上传文件失败 %s: %s", path, e)


def _write_status(cfg: Config, db: StateDb, current: Optional[str],
                  sent: int, total: int, err: Optional[str]) -> None:
    try:
        write_status(cfg.status_file, True, db.counts(), current, sent, total, err)
    except OSError as e:
        log.debug("写状态文件失败: %s", e)


def sync_pass(cfg: Config, db: StateDb) -> None:
    """处理当前所有 pending/uploading 文件，直到无待办或遇可重试错误。
    可被测试直接调用（不睡眠、不探活）。"""
    db.reset_errors()
    for path in find_tof_files(cfg.buffer_dir):
        session = session_id_of(path)
        try:
            validate_header(path)
            db.track(path, "tof", session, count_frames(path))
        except BadTofFile as e:
            dst = quarantine(cfg.buffer_dir, path)
            db.mark_error(path, "bad tof: %s -> %s" % (e, dst))
            log.error("坏 .tof 文件已隔离: %s -> %s", path, dst)
        except OSError:
            pass

    while not _stop:
        row = db.next_pending()
        if row is None:
            break
        ok = _process_file(cfg, db, row)
        if not ok:
            # 可重试错误：停止本轮，交由下一轮（避免空转）
            break


def main(argv: Optional[list] = None) -> int:
    cfg = parse_config(argv)
    _setup_logging(cfg)
    os.makedirs(cfg.buffer_dir, exist_ok=True)

    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT, _on_signal)

    db = StateDb(cfg.state_db)
    log.info("cloud_syncer 启动 cloud=%s buffer=%s", cfg.cloud_url, cfg.buffer_dir)

    try:
        while not _stop:
            if not health_ok(cfg.cloud_url, cfg.http_timeout):
                log.info("云端不可达，%ss 后重试", cfg.health_interval)
                _offline_status(cfg, db)
                _sleep(cfg.health_interval)
                continue
            sync_pass(cfg, db)
            if _stop:
                break
            _sleep(cfg.poll_interval)
    finally:
        db.close()
        log.info("cloud_syncer 退出")
    return 0


def _offline_status(cfg: Config, db: StateDb) -> None:
    try:
        write_status(cfg.status_file, False, db.counts(), None, 0, 0, "offline")
    except OSError:
        pass


def _sleep(seconds: float) -> None:
    end = time.time() + seconds
    while not _stop and time.time() < end:
        time.sleep(min(1.0, end - time.time()))


if __name__ == "__main__":
    raise SystemExit(main())
