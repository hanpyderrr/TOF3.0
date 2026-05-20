#!/usr/bin/env python3
"""检查 weston 客户端连接 + 重新读全部 weston 日志"""
import serial, time, sys

COM = "COM7"; BAUD = 1500000

def slow_write(s, data, delay=0.006):
    for i in range(0, len(data), 3):
        s.write(data[i:i+3]); time.sleep(delay)

def send_cmd(s, cmd, wait=2.5):
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

# weston 日志（完整，包含最新客户端连接信息）
print("=== weston.log full (recent) ===")
# tail -50 而不是 cat，weston 日志可能很长
print(send_cmd(s, "wc -l /tmp/weston.log ; tail -30 /tmp/weston.log", wait=3.0))

# qt_display 进程 + cpu 时间
print("=== qt_display proc stats ===")
print(send_cmd(s, "ps -o pid,stat,time,comm | grep qt_disp", wait=1.5))

# qt_display 内存映射（确认 QtWidgets 已 map）
print("=== qt_display maps (libs) ===")
print(send_cmd(s, "grep 'Qt5' /proc/905/maps 2>/dev/null | awk '{print $NF}' | sort -u | head -10"))

# qt.log 全部内容
print("=== qt.log complete ===")
print(send_cmd(s, "cat /tmp/qt.log", wait=2.0))

# 检查是否有 framebuffer/drm 节点
print("=== DRM/FB nodes ===")
print(send_cmd(s, "ls /dev/dri/ /dev/fb* 2>/dev/null"))

s.close(); print("[done]")
