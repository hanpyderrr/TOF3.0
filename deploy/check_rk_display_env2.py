#!/usr/bin/env python3
"""第二轮：检查 weston 启动方式，准备重启显示链"""
import serial, time, sys

COM = "COM7"
BAUD = 1500000

def slow_write(s, data, delay=0.006):
    chunk = 3
    for i in range(0, len(data), chunk):
        s.write(data[i:i+chunk])
        time.sleep(delay)

def send_cmd(s, cmd, wait=1.5):
    s.reset_input_buffer()
    slow_write(s, b'\x15')
    time.sleep(0.05)
    slow_write(s, (cmd + '\n').encode())
    time.sleep(wait)
    return s.read(s.in_waiting).decode(errors='replace')

try:
    s = serial.Serial(COM, BAUD, timeout=0.5)
    s.dtr = False
    time.sleep(0.3)
    print(f"[OK] {COM} @ {BAUD}")
except Exception as e:
    print(f"[ERR] {e}"); sys.exit(1)

# 1. 完整进程列表
print("=== ps aux ===")
print(send_cmd(s, "ps", wait=2.0))

# 2. weston 相关 init 脚本
print("=== /etc/init.d/ ===")
print(send_cmd(s, "ls /etc/init.d/"))

# 3. weston init 脚本内容
print("=== S50launcher or weston init ===")
print(send_cmd(s, "cat /etc/init.d/S50launcher 2>/dev/null || ls /etc/init.d/S5* 2>/dev/null || echo NO_S50"))

# 4. weston 可执行位置
print("=== weston binary ===")
print(send_cmd(s, "which weston 2>/dev/null || find /usr -name weston -type f 2>/dev/null | head -3"))

# 5. 检查 weston.ini
print("=== weston.ini ===")
print(send_cmd(s, "find / -name weston.ini 2>/dev/null | head -3 ; cat /etc/xdg/weston/weston.ini 2>/dev/null || echo NO_INI"))

s.close()
print("[done]")
