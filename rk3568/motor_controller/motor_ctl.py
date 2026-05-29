"""
motor_ctl.py — STM32 镜头电机串口控制（RK3568 侧）

链路：RK3568 /dev/ttyS4 → STM32F103（板内）→ TMC2209 ×2 → 电机

帧格式：FF 02 [device] [cmdHi] [cmdLo] [checksum]  (6 字节)
  checksum = (0x02 + device + cmdHi + cmdLo) & 0xFF

用法（模块）：
    from motor_ctl import MotorCtl
    m = MotorCtl()          # 默认 /dev/ttyS4
    m.slide_forward()
    m.gear_cw(rough=False)
    m.close()

用法（CLI）：
    python3 motor_ctl.py slide forward [rough]
    python3 motor_ctl.py slide back
    python3 motor_ctl.py gear cw [rough]
    python3 motor_ctl.py gear ccw
"""
from __future__ import annotations

import argparse
import sys

import serial

PORT_DEFAULT = "/dev/ttyS4"
BAUD = 19200

_DEV_SLIDE = 0x01
_DEV_GEAR  = 0x02

_SLIDE_FWD  = 0x20
_SLIDE_BACK = 0x22
_GEAR_CW    = 0x40
_GEAR_CCW   = 0x42

_ROUGH = 0x01
_FINE  = 0x02


class MotorCtl:
    def __init__(self, port: str = PORT_DEFAULT):
        self._ser = serial.Serial(port, BAUD, bytesize=8, parity="N",
                                  stopbits=1, timeout=0.1)

    def close(self):
        if self._ser.is_open:
            self._ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    # ---- public commands ----

    def slide_forward(self, rough: bool = True) -> None:
        self._send(_DEV_SLIDE, _SLIDE_FWD, _ROUGH if rough else _FINE)

    def slide_back(self, rough: bool = True) -> None:
        self._send(_DEV_SLIDE, _SLIDE_BACK, _ROUGH if rough else _FINE)

    def gear_cw(self, rough: bool = True) -> None:
        self._send(_DEV_GEAR, _GEAR_CW, _ROUGH if rough else _FINE)

    def gear_ccw(self, rough: bool = True) -> None:
        self._send(_DEV_GEAR, _GEAR_CCW, _ROUGH if rough else _FINE)

    # ---- internal ----

    def _send(self, device: int, cmd_hi: int, cmd_lo: int) -> None:
        chk = (0x02 + device + cmd_hi + cmd_lo) & 0xFF
        frame = bytes([0xFF, 0x02, device, cmd_hi, cmd_lo, chk])
        self._ser.write(frame)
        self._ser.flush()


def _parse_args(argv: list[str]) -> tuple[str, str, bool]:
    p = argparse.ArgumentParser(description="Motor control CLI")
    p.add_argument("device", choices=["slide", "gear"])
    p.add_argument("direction", choices=["forward", "back", "cw", "ccw"])
    p.add_argument("granularity", nargs="?", default="rough",
                   choices=["rough", "fine"])
    p.add_argument("--port", default=PORT_DEFAULT)
    args = p.parse_args(argv)
    return args.device, args.direction, args.granularity == "rough", args.port


def main(argv: list[str] | None = None) -> int:
    device, direction, rough, port = _parse_args(argv or sys.argv[1:])
    with MotorCtl(port) as m:
        fn = {
            ("slide", "forward"): m.slide_forward,
            ("slide", "back"):    m.slide_back,
            ("gear",  "cw"):      m.gear_cw,
            ("gear",  "ccw"):     m.gear_ccw,
        }.get((device, direction))
        if fn is None:
            print(f"invalid combination: {device} {direction}", file=sys.stderr)
            return 1
        fn(rough=rough)
        print(f"sent: {device} {direction} {'rough' if rough else 'fine'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
