#!/usr/bin/env python3
"""RK3568 显示环境诊断脚本 — 通过 COM7 串口逐步慢写"""
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
    slow_write(s, b'\x15')      # Ctrl-U 清行
    time.sleep(0.05)
    slow_write(s, (cmd + '\n').encode())
    time.sleep(wait)
    return s.read(s.in_waiting).decode(errors='replace')

try:
    s = serial.Serial(COM, BAUD, timeout=0.5)
    s.dtr = False
    time.sleep(0.3)
    print(f"[OK] opened {COM} @ {BAUD}")
except Exception as e:
    print(f"[ERR] {e}")
    sys.exit(1)

print("=== 1. weston + qt_display processes ===")
print(send_cmd(s, "ps | grep -E 'weston|qt_disp'"))

print("=== 2. wayland-0 socket ===")
print(send_cmd(s, "ls -la /var/run/wayland-0 2>&1"))

print("=== 3. env vars (XDG/QPA) ===")
# 用 sh -c 避免 shell 变量展开问题
print(send_cmd(s, "sh -c 'echo XDG=$XDG_RUNTIME_DIR QPA=$QT_QPA_PLATFORM'"))

print("=== 4. /etc/profile.d/weston.sh ===")
print(send_cmd(s, "cat /etc/profile.d/weston.sh 2>/dev/null || echo NO_FILE"))

print("=== 5. qt_display binary ===")
print(send_cmd(s, "ls -la /myApp/tof3/qt_display/"))

print("=== 6. received.dat status ===")
print(send_cmd(s, "ls -la /tmp/received.dat 2>&1 ; xxd /tmp/received.dat 2>/dev/null | head -2 || echo NO_FILE"))

s.close()
print("[done]")
