#!/usr/bin/env python3
"""修复 RK3568 上脚本的 CRLF → LF"""
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

for f in ["/etc/init.d/S95tof_spi_receiver", "/etc/init.d/S96tof_display"]:
    print(f"\n=== fix CRLF: {f} ===")
    out = rk_cmd(s, f"sed -i 's/\\r//' '{f}' && echo OK")
    print(out)

# 验证
print("\n=== test S95 status ===")
print(rk_cmd(s, "/etc/init.d/S95tof_spi_receiver status"))

print("\n=== test S96 status ===")
print(rk_cmd(s, "/etc/init.d/S96tof_display status"))

s.close()
print("[done]")
