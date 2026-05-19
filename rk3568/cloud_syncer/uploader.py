"""HTTP 客户端（urllib，标准库，板上无需 pip）。

契约（cloud/server/main.py）：
  GET  /api/health            -> 200 {"status":"ok"}
  POST /api/frames/depth      <- {"session_id","frames":[{seq,ts_ms,valid_count,depths_b64}]}
                              -> {"accepted": int}；depths_b64 须解码为恰好 2048B

错误分类：
  RetryableError  网络/超时/5xx —— 下轮重试，文件保留
  FatalError      4xx（坏数据）—— 文件应被隔离，不无限重试
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.request
from typing import List

from tof_parser import TofFrame


class RetryableError(Exception):
    pass


class FatalError(Exception):
    pass


def health_ok(base_url: str, timeout: float) -> bool:
    try:
        req = urllib.request.Request(base_url + "/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                return False
            body = json.loads(resp.read().decode("utf-8"))
            return body.get("status") == "ok"
    except Exception:
        return False


def post_depth(base_url: str, session_id: str, frames: List[TofFrame],
               timeout: float) -> int:
    """上传一批深度帧，返回云端 accepted 数。"""
    payload = {
        "session_id": session_id,
        "frames": [
            {
                "seq": fr.seq,
                "ts_ms": fr.ts_ms,
                "valid_count": fr.valid_count,
                "depths_b64": base64.b64encode(fr.depths).decode("ascii"),
            }
            for fr in frames
        ],
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url + "/api/frames/depth",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return int(body.get("accepted", 0))
    except urllib.error.HTTPError as e:
        if 400 <= e.code < 500:
            raise FatalError("HTTP %d: %s" % (e.code, e.reason))
        raise RetryableError("HTTP %d: %s" % (e.code, e.reason))
    except urllib.error.URLError as e:
        raise RetryableError("URLError: %s" % (e.reason,))
    except Exception as e:  # 超时、连接重置等
        raise RetryableError("%s: %s" % (type(e).__name__, e))
