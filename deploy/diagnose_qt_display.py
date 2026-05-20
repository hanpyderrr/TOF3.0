#!/usr/bin/env python3
"""诊断 qt_display 为何无日志输出"""
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

# 1. weston 完整日志（可能有 Qt 客户端连接记录）
print("=== weston.log (full) ===")
print(send_cmd(s, "cat /tmp/weston.log", wait=3.0))

# 2. /var/run 实际结构
print("=== /var/run contents ===")
print(send_cmd(s, "ls -la /var/run/"))

# 3. qt_display fd 看连接
print("=== qt_display open files ===")
pid_out = send_cmd(s, "cat /var/run/mydisplay.pid 2>/dev/null || echo NOPID")
print(f"mydisplay.pid: {pid_out.strip()}")
print(send_cmd(s, "ls -la /proc/905/fd 2>/dev/null | head -20"))

# 4. 查 qt_display 链接的 so
print("=== qt_display linked libs ===")
print(send_cmd(s, "ldd /myApp/tof3/qt_display/qt_display 2>/dev/null | head -20"))

# 5. 直接前台运行一下，看屏幕输出
print("=== run qt_display foreground 3s ===")
print(send_cmd(s,
    ". /etc/profile && timeout 3 /myApp/tof3/qt_display/qt_display /tmp/received.dat",
    wait=5.0))

s.close(); print("[done]")
