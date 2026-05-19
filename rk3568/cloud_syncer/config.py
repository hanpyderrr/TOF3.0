"""cloud_syncer 配置。

来源优先级：命令行 > 环境变量(TOF_CS_*) > 默认。
不硬编码 IP/端口/路径（遵守项目约束）。Python 3.8，仅标准库。
"""
from __future__ import annotations

import argparse
import os
from typing import Optional


class Config:
    def __init__(
        self,
        cloud_url: str,
        buffer_dir: str,
        poll_interval: float,
        health_interval: float,
        depth_batch: int,
        max_retry: int,
        http_timeout: float,
        state_db: str,
        status_file: str,
        delete_after_upload: bool,
        log_file: Optional[str],
        log_level: str,
    ) -> None:
        self.cloud_url = cloud_url.rstrip("/")
        self.buffer_dir = os.path.expanduser(buffer_dir)
        self.poll_interval = poll_interval
        self.health_interval = health_interval
        self.depth_batch = depth_batch
        self.max_retry = max_retry
        self.http_timeout = http_timeout
        self.state_db = os.path.expanduser(state_db)
        self.status_file = os.path.expanduser(status_file)
        self.delete_after_upload = delete_after_upload
        self.log_file = os.path.expanduser(log_file) if log_file else None
        self.log_level = log_level.upper()


def _env(name: str, default: str) -> str:
    return os.environ.get("TOF_CS_" + name, default)


def parse_config(argv: Optional[list] = None) -> Config:
    p = argparse.ArgumentParser(
        prog="cloud_syncer",
        description="RK3568 5G 上传：扫描 ~/tof-buffer/ 的 .tof 深度文件 POST 到云端 FastAPI",
    )
    p.add_argument("--cloud-url", default=_env("CLOUD_URL", ""),
                   help="云端 FastAPI 基址，如 http://1.2.3.4:8765（必填）")
    p.add_argument("--buffer-dir", default=_env("BUFFER_DIR", "~/tof-buffer"))
    p.add_argument("--poll-interval", type=float, default=float(_env("POLL_INTERVAL", "10")))
    p.add_argument("--health-interval", type=float, default=float(_env("HEALTH_INTERVAL", "30")))
    p.add_argument("--depth-batch", type=int, default=int(_env("DEPTH_BATCH", "50")))
    p.add_argument("--max-retry", type=int, default=int(_env("MAX_RETRY", "5")))
    p.add_argument("--http-timeout", type=float, default=float(_env("HTTP_TIMEOUT", "30")))
    p.add_argument("--state-db", default=_env("STATE_DB", "~/tof-buffer/.cloud_syncer.db"))
    p.add_argument("--status-file", default=_env("STATUS_FILE", "~/tof-buffer/.upload_status.json"))
    p.add_argument("--no-delete", action="store_true",
                   help="上传成功后保留本地文件（默认删除以回收配额）")
    p.add_argument("--log-file", default=_env("LOG_FILE", "") or None)
    p.add_argument("--log-level", default=_env("LOG_LEVEL", "INFO"))
    args = p.parse_args(argv)

    if not args.cloud_url:
        p.error("缺少 --cloud-url（或环境变量 TOF_CS_CLOUD_URL）")

    return Config(
        cloud_url=args.cloud_url,
        buffer_dir=args.buffer_dir,
        poll_interval=args.poll_interval,
        health_interval=args.health_interval,
        depth_batch=args.depth_batch,
        max_retry=args.max_retry,
        http_timeout=args.http_timeout,
        state_db=args.state_db,
        status_file=args.status_file,
        delete_after_upload=not args.no_delete,
        log_file=args.log_file,
        log_level=args.log_level,
    )
