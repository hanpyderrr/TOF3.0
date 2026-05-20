#!/usr/bin/env python3
"""
关闭 stdio 缓冲运行 qt_display，立即捕获 qInfo 输出
"""
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

# 1. 杀掉旧的后台 qt_display
print("=== kill bg qt_display ===")
print(send_cmd(s, "killall qt_display 2>/dev/null ; sleep 0.5 ; echo KILLED"))

# 2. 用 stdbuf 无缓冲跑 5s，捕获输出
print("=== run qt_display (no buffer, 5s) ===")
# QT_LOGGING_RULES 确保 *.info=true (有些 build 会关掉 info)
cmd = (". /etc/profile && "
       "QT_LOGGING_RULES='*.debug=true;*.info=true' "
       "stdbuf -oL -eL "
       "/myApp/tof3/qt_display/qt_display /tmp/received.dat "
       "> /tmp/qt2.log 2>&1 &")
print(send_cmd(s, cmd, wait=1.0))
print("  sleeping 5s ...")
time.sleep(5)

print(send_cmd(s, "cat /tmp/qt2.log", wait=2.0))

# 3. 检查进程状态
print("=== process check ===")
print(send_cmd(s, "ps | grep qt_disp"))

s.close(); print("[done]")
