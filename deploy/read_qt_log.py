#!/usr/bin/env python3
"""读 qt_display 和 weston 日志，检查状态"""
import serial, time, sys

COM = "COM7"; BAUD = 1500000

def slow_write(s, data, delay=0.006):
    for i in range(0, len(data), 3):
        s.write(data[i:i+3]); time.sleep(delay)

def send_cmd(s, cmd, wait=2.0):
    s.reset_input_buffer()
    slow_write(s, b'\x15'); time.sleep(0.05)
    slow_write(s, (cmd + '\n').encode())
    time.sleep(wait)
    return s.read(s.in_waiting).decode(errors='replace')

try:
    s = serial.Serial(COM, BAUD, timeout=0.5); s.dtr = False; time.sleep(0.3)
    print(f"[OK] {COM}")
except Exception as e:
    print(f"[ERR] {e}"); sys.exit(1)

print("=== qt_display log ===")
print(send_cmd(s, "cat /tmp/qt.log", wait=2.0))

print("=== weston log (tail) ===")
print(send_cmd(s, "tail -20 /tmp/weston.log", wait=2.0))

print("=== process check ===")
print(send_cmd(s, "ps | grep -E 'weston|qt_disp'"))

# 检查 /var/run 是否是 symlink（Qt 警告原因）
print("=== /var/run type ===")
print(send_cmd(s, "ls -la / | grep 'var'"))

s.close(); print("[done]")
