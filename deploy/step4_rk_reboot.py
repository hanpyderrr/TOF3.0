#!/usr/bin/env python3
"""Step 4: re-upload RK3568 autostart scripts, then reboot."""
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

def upload_file(s, local_path, remote_path):
    """Upload a file over serial through base64 chunking."""
    import base64
    with open(local_path, 'rb') as f:
        data = f.read()
    data = data.replace(b'\r\n', b'\n')
    b64 = base64.b64encode(data).decode()
    tmp = remote_path + '.b64'
    rk_cmd(s, f"rm -f '{tmp}'", wait=0.3)
    CHUNK = 60
    for i in range(0, len(b64), CHUNK):
        seg = b64[i:i+CHUNK]
        rk_cmd(s, f"printf '%s' '{seg}' >> '{tmp}'", wait=0.2)
    out = rk_cmd(s, f"base64 -d '{tmp}' > '{remote_path}' && chmod +x '{remote_path}' && ls -la '{remote_path}'", wait=1.5)
    rk_cmd(s, f"rm -f '{tmp}'", wait=0.3)
    return out

try:
    s = serial.Serial(COM, BAUD, timeout=0.5); s.dtr = False; time.sleep(0.3)
    print(f"[OK] {COM}")
except Exception as e:
    print(f"[ERR] {e}"); sys.exit(1)

BASE = r"E:\vs-workspace\TOF3.0\rk3568\autostart"

print("\n=== upload S95tof_spi_receiver ===")
out = upload_file(s, f"{BASE}\\S95tof_spi_receiver", "/etc/init.d/S95tof_spi_receiver")
print(out)

print("\n=== upload S96tof_display ===")
out = upload_file(s, f"{BASE}\\S96tof_display", "/etc/init.d/S96tof_display")
print(out)

print("\n=== reboot RK3568 ===")
print(rk_cmd(s, "reboot", wait=2.0))
print("[rebooting...]")
s.close()
