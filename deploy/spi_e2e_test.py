#!/usr/bin/env python3
"""SPI end-to-end smoke test: Nezha depth frame -> RK3568 received.dat.

The script is intended to run on the development host. It uses SSH to start
Nezha acquisition/spi_syncer and a serial shell to reset the RK3568 USB-SPI
adapter, start spi_receiver/qt_display, then poll /tmp/received.dat.
"""

from __future__ import annotations

import argparse
import os
import re
import struct
import sys
import time
from dataclasses import dataclass

if os.name != "nt":
    import select
    import termios
    import tty
else:  # pragma: no cover - compile/import support on Windows hosts
    select = None
    termios = None
    tty = None

FRAME_SIZE = 2070
MAGIC = 0x50464F54
MAX_DEPTH_MM = 8450


def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = ((crc >> 1) ^ 0xA001) if (crc & 1) else (crc >> 1)
            crc &= 0xFFFF
    return crc


def validate_frame(frame: bytes) -> tuple[bool, str]:
    if len(frame) != FRAME_SIZE:
        return False, f"short read: {len(frame)} bytes"
    magic, version, header_size = struct.unpack_from("<IBB", frame, 0)
    if magic != MAGIC:
        return False, f"bad magic: 0x{magic:08x}"
    if version != 1 or header_size != 16:
        return False, f"bad header: version={version} header_size={header_size}"
    seq = struct.unpack_from("<I", frame, 8)[0]
    width, height = struct.unpack_from("<HH", frame, 12)
    if (width, height) != (32, 32):
        return False, f"bad dimensions: {width}x{height}"
    valid_count = struct.unpack_from("<H", frame, 16)[0]
    depths = struct.unpack_from("<1024H", frame, 20)
    actual_valid = sum(1 for d in depths if d != 0)
    if any(d > MAX_DEPTH_MM for d in depths):
        return False, "depth out of range"
    if actual_valid != valid_count:
        return False, f"validCount mismatch: header={valid_count} actual={actual_valid}"
    expected_crc = struct.unpack_from("<H", frame, FRAME_SIZE - 2)[0]
    actual_crc = crc16_modbus(frame[4 : FRAME_SIZE - 2])
    if actual_crc != expected_crc:
        return False, f"CRC mismatch: expected=0x{expected_crc:04x} actual=0x{actual_crc:04x}"
    return True, f"seq={seq} valid={valid_count} crc=0x{actual_crc:04x}"


def sh_quote(s: str) -> str:
    return "'" + s.replace("'", "'\"'\"'") + "'"


class NezhaSSH:
    def __init__(self, host: str, user: str, password: str, port: int) -> None:
        try:
            import paramiko
        except ImportError as exc:  # pragma: no cover - runtime dependency check
            raise SystemExit("paramiko is required: python3 -m pip install paramiko") from exc

        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.client.connect(host, port=port, username=user, password=password, timeout=20)

    def run(self, cmd: str, check: bool = True) -> str:
        print(f"[nezha] $ {cmd}")
        _, stdout, stderr = self.client.exec_command(cmd)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        text = (out + err).strip()
        if text:
            print(text)
        if check:
            rc = stdout.channel.recv_exit_status()
            if rc != 0:
                raise RuntimeError(f"Nezha command failed rc={rc}: {cmd}\n{text}")
        return text

    def close(self) -> None:
        self.client.close()


class SerialShell:
    def __init__(self, device: str, baud: int, timeout: float = 8.0) -> None:
        if termios is None or tty is None or select is None:
            raise RuntimeError("serial control needs POSIX termios; run from Linux/WSL")
        self.device = device
        self.timeout = timeout
        self.fd = os.open(device, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
        attrs = termios.tcgetattr(self.fd)
        speed = getattr(termios, f"B{baud}", None)
        if speed is None:
            raise RuntimeError(f"unsupported baud rate for termios: {baud}")
        attrs[0] = 0
        attrs[1] = 0
        attrs[2] = termios.CLOCAL | termios.CREAD | termios.CS8
        attrs[3] = 0
        attrs[4] = speed
        attrs[5] = speed
        termios.tcsetattr(self.fd, termios.TCSANOW, attrs)
        tty.setraw(self.fd)
        self.write("\n")
        time.sleep(0.3)
        self.drain()

    def write(self, text: str) -> None:
        os.write(self.fd, text.encode())

    def drain(self) -> str:
        chunks: list[bytes] = []
        end = time.time() + 0.5
        while time.time() < end:
            r, _, _ = select.select([self.fd], [], [], 0.05)
            if not r:
                continue
            try:
                chunks.append(os.read(self.fd, 4096))
            except BlockingIOError:
                pass
        return b"".join(chunks).decode(errors="replace")

    def run(self, cmd: str, timeout: float | None = None) -> str:
        marker = f"__CODEx_DONE_{int(time.time() * 1000)}__"
        full_cmd = f"{cmd}\nprintf '{marker}:%s\\n' \"$?\"\n"
        print(f"[rk3568] $ {cmd}")
        self.write(full_cmd)
        deadline = time.time() + (timeout or self.timeout)
        data = ""
        while time.time() < deadline:
            r, _, _ = select.select([self.fd], [], [], 0.1)
            if not r:
                continue
            data += os.read(self.fd, 4096).decode(errors="replace")
            m = re.search(re.escape(marker) + r":(\d+)", data)
            if m:
                rc = int(m.group(1))
                cleaned = data.split(marker, 1)[0].strip()
                if cleaned:
                    print(cleaned)
                if rc != 0:
                    raise RuntimeError(f"RK3568 command failed rc={rc}: {cmd}\n{cleaned}")
                return cleaned
        raise TimeoutError(f"timeout waiting for RK3568 command: {cmd}")

    def close(self) -> None:
        os.close(self.fd)


def rk_usb_reset_cmd() -> str:
    return r"""
for d in /sys/bus/usb/devices/*; do
    [ -f "$d/idVendor" ] || continue
    vid="$(cat "$d/idVendor" 2>/dev/null)"
    pid="$(cat "$d/idProduct" 2>/dev/null)"
    if [ "$vid:$pid" = "0483:5740" ]; then
        n="$(basename "$d")"
        echo "$n" > /sys/bus/usb/drivers/usb/unbind
        sleep 1
        echo "$n" > /sys/bus/usb/drivers/usb/bind
        echo "reset $n $vid:$pid"
        exit 0
    fi
done
echo "USB-SPI adapter 0483:5740 not found"
exit 1
""".strip()


def rk_poll_frame_cmd(path: str) -> str:
    return (
        "python3 -c "
        + sh_quote(
            "import binascii,sys;"
            f"p={path!r};"
            "\ntry:\n d=open(p,'rb').read()\nexcept Exception as e:\n print('ERR',e); sys.exit(0)\n"
            "print('LEN',len(d));"
            "print('HEX',binascii.hexlify(d).decode())"
        )
    )


@dataclass
class Args:
    nezha_host: str
    nezha_user: str
    nezha_password: str
    nezha_sudo_password: str
    nezha_port: int
    rk_serial: str
    rk_baud: int
    depth_file: str
    spidev: str
    received_dat: str
    nezha_root: str
    rk_root: str
    timeout: int
    start_qt: bool


def parse_args() -> Args:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--nezha-host", default="192.168.31.127")
    p.add_argument("--nezha-user", default="ding")
    p.add_argument("--nezha-password", default="1234")
    p.add_argument("--nezha-sudo-password", default=None)
    p.add_argument("--nezha-port", type=int, default=22)
    p.add_argument("--rk-serial", default="/dev/ttyUSB0")
    p.add_argument("--rk-baud", type=int, default=1500000)
    p.add_argument("--depth-file", default="/tmp/depth.dat")
    p.add_argument("--spidev", default="/dev/spidev1.0")
    p.add_argument("--received-dat", default="/tmp/received.dat")
    p.add_argument("--nezha-root", default="~/TOF3.0")
    p.add_argument("--rk-root", default="/myApp/tof3")
    p.add_argument("--timeout", type=int, default=30)
    p.add_argument("--start-qt", action="store_true", help="also start RK3568 qt_display")
    ns = p.parse_args()
    if ns.nezha_sudo_password is None:
        ns.nezha_sudo_password = ns.nezha_password
    return Args(**vars(ns))


def main() -> int:
    args = parse_args()

    if os.name == "nt":
        raise SystemExit("serial control in this script needs POSIX termios; run from Linux/WSL")

    nezha = NezhaSSH(args.nezha_host, args.nezha_user, args.nezha_password, args.nezha_port)
    rk = SerialShell(args.rk_serial, args.rk_baud)
    try:
        nezha.run(f"cd {args.nezha_root}/nezha/acquisition && test -x ./sim_pf32")
        nezha.run(f"cd {args.nezha_root}/nezha/spi_syncer && test -x ./spi_syncer || make")
        nezha.run("pkill -f 'sim_pf32|spi_syncer' 2>/dev/null || true", check=False)
        nezha.run(
            f"nohup {args.nezha_root}/nezha/acquisition/sim_pf32 "
            f"> /tmp/sim_pf32.log 2>&1 &"
        )
        time.sleep(2)
        sudo_cmd = (
            f"nohup {args.nezha_root}/nezha/spi_syncer/spi_syncer "
            f"{sh_quote(args.depth_file)} {sh_quote(args.spidev)} "
            f"> /tmp/spi_syncer.log 2>&1 &"
        )
        nezha.run(
            "printf '%s\\n' "
            f"{sh_quote(args.nezha_sudo_password)} | sudo -S sh -c {sh_quote(sudo_cmd)}"
        )

        rk.run("pkill -f 'spi_receiver|qt_display' 2>/dev/null || true", timeout=5)
        rk.run(rk_usb_reset_cmd(), timeout=10)
        time.sleep(2)
        rk.run(f"rm -f {sh_quote(args.received_dat)}")
        rk.run(
            f"nohup {args.rk_root}/spi_receiver/spi_receiver {sh_quote(args.received_dat)} "
            f"> /tmp/spi_receiver.log 2>&1 &",
            timeout=5,
        )
        if args.start_qt:
            rk.run(
                ". /etc/profile 2>/dev/null || true; "
                "export XDG_RUNTIME_DIR=${XDG_RUNTIME_DIR:-/var/run}; "
                "export QT_QPA_PLATFORM=${QT_QPA_PLATFORM:-wayland}; "
                f"nohup {args.rk_root}/qt_display/qt_display {sh_quote(args.received_dat)} "
                "> /tmp/qt_display.log 2>&1 &",
                timeout=5,
            )

        deadline = time.time() + args.timeout
        last_seq = None
        while time.time() < deadline:
            out = rk.run(rk_poll_frame_cmd(args.received_dat), timeout=8)
            hex_match = re.search(r"HEX\s+([0-9a-fA-F]+)", out)
            if hex_match:
                frame = bytes.fromhex(hex_match.group(1))
                ok, msg = validate_frame(frame)
                print(f"[verify] {msg}")
                if ok:
                    seq = struct.unpack_from("<I", frame, 8)[0]
                    if last_seq is None or seq != last_seq:
                        print(f"[PASS] received valid frame: {msg}")
                        return 0
                    print(f"[verify] seq did not advance yet: {seq}")
                    last_seq = seq
            time.sleep(1)

        print("[FAIL] timed out waiting for a valid received.dat frame", file=sys.stderr)
        rk.run("tail -40 /tmp/spi_receiver.log 2>/dev/null || true", timeout=5)
        nezha.run("tail -40 /tmp/spi_syncer.log 2>/dev/null || true", check=False)
        return 1
    finally:
        rk.close()
        nezha.close()


if __name__ == "__main__":
    raise SystemExit(main())
