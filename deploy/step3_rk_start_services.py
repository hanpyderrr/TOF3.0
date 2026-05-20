#!/usr/bin/env python3
"""步骤3：RK3568 启动新服务（S95 spi_receiver + S96 qt_display）"""
import serial, time, sys

COM = "COM7"; BAUD = 1500000

def slow_write(s, data, delay=0.006):
    for i in range(0, len(data), 3):
        s.write(data[i:i+3]); time.sleep(delay)

def rk_cmd(s, cmd, wait=2.0):
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

# 检查当前状态
print("=== current procs ===")
print(rk_cmd(s, "ps | grep -E 'weston|qt_disp|spi_rec' | grep -v grep"))

# 确保 weston 在跑
print("\n=== ensure weston running ===")
out = rk_cmd(s, "ls /var/run/wayland-0 2>/dev/null && echo WESTON_UP || echo WESTON_DOWN", wait=1.0)
if "WESTON_DOWN" in out:
    print("  weston not running, starting...")
    rk_cmd(s, ". /etc/profile && /usr/bin/weston > /tmp/weston.log 2>&1 &", wait=3.0)
    for _ in range(8):
        out = rk_cmd(s, "ls /var/run/wayland-0 2>/dev/null && echo UP || echo WAIT", wait=1.0)
        if "UP" in out:
            print("  weston up"); break
        time.sleep(1)
else:
    print("  weston already up")

# 停掉旧的 qt_display（如果在跑）
print("\n=== stop old qt_display ===")
print(rk_cmd(s, "killall qt_display 2>/dev/null && echo KILLED || echo NOT_RUNNING", wait=1.0))

# 启动 S95 (USB reset + spi_receiver)
print("\n=== start S95tof_spi_receiver ===")
print(rk_cmd(s, "/etc/init.d/S95tof_spi_receiver start", wait=5.0))

# 启动 S96 (qt_display)
print("\n=== start S96tof_display ===")
print(rk_cmd(s, "/etc/init.d/S96tof_display start", wait=3.0))

# 等 3s 再查状态
time.sleep(3)

print("\n=== service status ===")
print(rk_cmd(s, "/etc/init.d/S95tof_spi_receiver status"))
print(rk_cmd(s, "/etc/init.d/S96tof_display status"))

print("\n=== process list ===")
print(rk_cmd(s, "ps | grep -E 'weston|qt_disp|spi_rec' | grep -v grep"))

print("\n=== spi_receiver log (last 10) ===")
print(rk_cmd(s, "tail -10 /var/log/tof_spi_receiver.log 2>/dev/null || echo EMPTY"))

print("\n=== qt_display log (last 5) ===")
print(rk_cmd(s, "tail -5 /var/log/tof_display.log 2>/dev/null || echo EMPTY"))

s.close()
print("[done]")
