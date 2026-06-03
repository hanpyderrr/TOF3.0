#!/usr/bin/env python3
"""
发送 YSC-SO-M04-4 外触发使能命令（Modbus RTU）。
用法: python3 laser_init.py [串口] [动作]
  串口: /dev/ttyUSB1 或 /dev/ttyS4 等，默认 /dev/ttyUSB1
  动作: ext(外触发,默认) | int(内触发) | off(关闭)
"""
import sys, serial, struct, time

PORT   = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB1"
ACTION = sys.argv[2] if len(sys.argv) > 2 else "ext"

DEVICE_ADDR   = 0x01
FUNC_TRIGGER  = 0x04
DATA_EXT      = 0x02
DATA_INT      = 0x01
DATA_OFF      = 0x00

def crc16(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if crc & 1 else crc >> 1
    return crc

def build_frame(func: int, data: int) -> bytes:
    payload = struct.pack(">BBBBBB", DEVICE_ADDR, func,
                          (data >> 24) & 0xFF, (data >> 16) & 0xFF,
                          (data >> 8) & 0xFF, data & 0xFF)
    crc = crc16(payload)
    return payload + struct.pack("<H", crc)

ACTION_MAP = {"ext": DATA_EXT, "int": DATA_INT, "off": DATA_OFF}
if ACTION not in ACTION_MAP:
    print(f"未知动作: {ACTION}，可选 ext/int/off"); sys.exit(1)

frame = build_frame(FUNC_TRIGGER, ACTION_MAP[ACTION])
print(f"串口: {PORT}  动作: {ACTION}  帧: {frame.hex()}")

with serial.Serial(PORT, 9600, timeout=1) as s:
    s.write(frame)
    time.sleep(0.1)
    resp = s.read(64)
    print(f"响应: {resp.hex() if resp else '(无响应)'}")

print("完成")
