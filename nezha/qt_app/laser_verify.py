"""
laser_verify.py — 哪吒侧激光器 Modbus RTU 串口验证脚本

用法：
    python3 laser_verify.py --port /dev/ttyS4
    python3 laser_verify.py --port /dev/ttyS4 --scan   # 扫描所有 ttyS 节点
    python3 laser_verify.py --port /dev/ttyS4 --set-level 10

协议：YSC-SO-M04-4，Modbus RTU 9600 8N1
帧格式：[func 1B][data 4B big-endian][CRC16 2B little-endian]
"""
from __future__ import annotations

import argparse
import struct
import sys
import time

import serial


BAUD = 9600

# 功能码
FUNC_VOLTAGE  = 0x01
FUNC_FREQ     = 0x02
FUNC_PULSE    = 0x03
FUNC_TRIGGER  = 0x04
FUNC_READ     = 0x06


def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def build_frame(func: int, data: int) -> bytes:
    payload = bytes([func]) + struct.pack(">I", data)  # 1B func + 4B big-endian
    crc = crc16(payload)
    return payload + struct.pack("<H", crc)             # 2B CRC little-endian


def send_recv(ser: serial.Serial, frame: bytes, timeout: float = 0.3) -> bytes:
    ser.reset_input_buffer()
    ser.write(frame)
    ser.flush()
    time.sleep(timeout)
    return ser.read(ser.in_waiting or 64)


def parse_read_response(resp: bytes) -> None:
    """解析 func=0x06 的读取响应（手册示例 13–14 字节，字段存疑待实物核实）"""
    print(f"  原始响应 ({len(resp)} 字节): {resp.hex(' ').upper()}")
    if len(resp) < 7:
        print("  响应太短，可能未收到或帧错误")
        return

    func = resp[0]
    print(f"  func=0x{func:02X}", end="")
    if func != FUNC_READ:
        print(f"  ← 非预期功能码")
        return
    print()

    # 手册返回示例：06 00 15 00 00 13 88 00 06 00 00 E8 41
    # 字段映射存疑（手册表格13B vs 示例14B 自相矛盾），按示例猜测：
    if len(resp) >= 13:
        voltage_level = struct.unpack(">H", resp[1:3])[0]   # bytes 1-2
        freq_hz       = struct.unpack(">I", resp[3:7])[0]    # bytes 3-6 (示例: 0x00001388=5000)
        pulse_x5ns    = struct.unpack(">H", resp[7:9])[0]    # bytes 7-8 (示例: 0x0006=6→30ns)
        # bytes 9-10: 未知（示例 00 00）
        print(f"  电压等级(猜): {voltage_level}")
        print(f"  频率(猜):     {freq_hz} Hz")
        print(f"  脉宽(猜):     {pulse_x5ns * 5} ns")
        print("  ⚠ 字段映射未经实物验证，仅供参考")
    else:
        print("  字节数不足，无法解析字段")


def try_port(port: str) -> bool:
    """向指定端口发一帧读参数，返回是否有有效响应"""
    try:
        with serial.Serial(port, BAUD, bytesize=8, parity="N",
                           stopbits=1, timeout=0.5) as ser:
            frame = build_frame(FUNC_READ, 0)
            resp = send_recv(ser, frame)
            if resp and resp[0] == FUNC_READ:
                print(f"  {port}: ✓ 有响应，func=0x06")
                return True
            elif resp:
                print(f"  {port}: 收到数据但 func 不对: {resp.hex()}")
            else:
                print(f"  {port}: 无响应")
    except serial.SerialException as e:
        print(f"  {port}: 打开失败 ({e})")
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyS4")
    ap.add_argument("--scan", action="store_true",
                    help="扫描 /dev/ttyS0-7，找激光器在哪个节点")
    ap.add_argument("--set-level", type=int, metavar="N",
                    help="设置电压等级(1-200)")
    ap.add_argument("--set-external-trigger", action="store_true",
                    help="切换为外触发模式（PF32 sys_master 时必须）")
    args = ap.parse_args()

    if args.scan:
        print("扫描串口节点...")
        found = []
        for i in range(8):
            p = f"/dev/ttyS{i}"
            if try_port(p):
                found.append(p)
        print(f"\n找到激光器节点: {found or '无'}")
        return 0

    print(f"连接 {args.port} @ {BAUD} 8N1")
    try:
        ser = serial.Serial(args.port, BAUD, bytesize=8, parity="N",
                            stopbits=1, timeout=0.5)
    except serial.SerialException as e:
        print(f"打开串口失败: {e}", file=sys.stderr)
        return 1

    with ser:
        # 1. 读当前参数
        print("\n[1] 读取当前参数 (func=0x06)...")
        frame = build_frame(FUNC_READ, 0)
        print(f"  发送: {frame.hex(' ').upper()}")
        resp = send_recv(ser, frame)
        parse_read_response(resp)

        # 2. 可选：设置电压等级
        if args.set_level is not None:
            lvl = max(1, min(200, args.set_level))
            print(f"\n[2] 设置电压等级 = {lvl} (func=0x01)...")
            frame = build_frame(FUNC_VOLTAGE, lvl)
            print(f"  发送: {frame.hex(' ').upper()}")
            resp = send_recv(ser)
            if resp:
                print(f"  响应: {resp.hex(' ').upper()}")
                if resp == frame:
                    print("  ✓ 响应与发送一致（设置成功）")
            else:
                print("  无响应")

        # 3. 可选：切外触发
        if args.set_external_trigger:
            print("\n[3] 切换外触发模式 (func=0x04, data=0x02)...")
            frame = build_frame(FUNC_TRIGGER, 2)
            print(f"  发送: {frame.hex(' ').upper()}")
            resp = send_recv(ser)
            if resp:
                print(f"  响应: {resp.hex(' ').upper()}")
                if resp == frame:
                    print("  ✓ 外触发设置成功")
            else:
                print("  无响应")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
