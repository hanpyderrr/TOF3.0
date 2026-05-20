#!/usr/bin/env python3
"""读 S49weston、S51mydisplay 脚本内容"""
import serial, time, sys

COM = "COM7"
BAUD = 1500000

def slow_write(s, data, delay=0.006):
    chunk = 3
    for i in range(0, len(data), chunk):
        s.write(data[i:i+chunk])
        time.sleep(delay)

def send_cmd(s, cmd, wait=2.0):
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

print("=== S49weston ===")
print(send_cmd(s, "cat /etc/init.d/S49weston"))

print("=== S51mydisplay ===")
print(send_cmd(s, "cat /etc/init.d/S51mydisplay"))

print("=== S99myspireceive ===")
print(send_cmd(s, "cat /etc/init.d/S99myspireceive"))

s.close()
print("[done]")
