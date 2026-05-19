"""标准库 mock 云端，模拟 cloud/server/main.py 的相关契约（无需 FastAPI）。

- GET  /api/health        -> 200 {"status":"ok"}
- POST /api/frames/depth  -> 校验每帧 depths_b64 解码=2048B，记录 (session,seq)，
                             返回 {"accepted":N}
- 支持 fail_after：前若干次 POST 正常，之后返回 503（模拟断网/5xx，测试续传）

received：list[(session_id, seq)]，用于断言无重复、总数正确。
"""
from __future__ import annotations

import base64
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import List, Optional, Tuple


class MockState:
    def __init__(self) -> None:
        self.received = []  # type: List[Tuple[str, int]]
        self.post_count = 0
        self.fail_mode = False               # True 时 POST 一律 503
        self.fail_after = None  # type: Optional[int]  # 前 N 次成功，之后 503
        self.lock = threading.Lock()


class _Handler(BaseHTTPRequestHandler):
    state = None  # type: Optional[MockState]

    def log_message(self, *a):  # 静默
        pass

    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/health":
            self._json(200, {"status": "ok"})
        else:
            self._json(404, {"detail": "not found"})

    def do_POST(self):
        st = _Handler.state
        if self.path != "/api/frames/depth":
            self._json(404, {"detail": "not found"})
            return

        with st.lock:
            st.post_count += 1
            failing = st.fail_mode or (
                st.fail_after is not None and st.post_count > st.fail_after
            )
        if failing:
            self._json(503, {"detail": "simulated outage"})
            return

        n = int(self.headers.get("Content-Length", "0"))
        try:
            payload = json.loads(self.rfile.read(n).decode("utf-8"))
            session = payload["session_id"]
            frames = payload["frames"]
            rows = []
            for fr in frames:
                blob = base64.b64decode(fr["depths_b64"], validate=True)
                if len(blob) != 2048:
                    self._json(400, {"detail": "depths_b64 must be 2048B"})
                    return
                rows.append((session, int(fr["seq"])))
        except Exception as e:  # noqa: BLE001
            self._json(400, {"detail": "bad payload: %s" % e})
            return

        with st.lock:
            st.received.extend(rows)
        self._json(200, {"accepted": len(rows)})


class MockCloud:
    def __init__(self) -> None:
        self.state = MockState()
        _Handler.state = self.state
        self._srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.port = self._srv.server_address[1]
        self._t = threading.Thread(target=self._srv.serve_forever, daemon=True)

    @property
    def base_url(self) -> str:
        return "http://127.0.0.1:%d" % self.port

    def start(self) -> None:
        self._t.start()

    def stop(self) -> None:
        self._srv.shutdown()
        self._srv.server_close()

    # 测试辅助
    def reset(self) -> None:
        with self.state.lock:
            self.state.received = []
            self.state.post_count = 0
            self.state.fail_mode = False
            self.state.fail_after = None

    def set_fail(self, on: bool) -> None:
        with self.state.lock:
            self.state.fail_mode = on

    def set_fail_after(self, n: Optional[int]) -> None:
        with self.state.lock:
            self.state.fail_after = n
            self.state.post_count = 0

    @property
    def received(self):
        with self.state.lock:
            return list(self.state.received)
