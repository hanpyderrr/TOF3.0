#!/usr/bin/env python3
"""步骤2：部署新 autostart 脚本到 RK3568，禁用旧 S51mydisplay"""
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
    """通过 base64 串口传文件"""
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

# 1. 上传 S95tof_spi_receiver
print("\n=== upload S95tof_spi_receiver ===")
out = upload_file(s, f"{BASE}\\S95tof_spi_receiver", "/etc/init.d/S95tof_spi_receiver")
print(out)

# 2. 上传 S96tof_display
print("\n=== upload S96tof_display ===")
out = upload_file(s, f"{BASE}\\S96tof_display", "/etc/init.d/S96tof_display")
print(out)

# 3. 禁用旧 S51mydisplay（改名加 .old 后缀）
print("\n=== disable old S51mydisplay ===")
out = rk_cmd(s,
    "mv /etc/init.d/S51mydisplay /etc/init.d/S51mydisplay.old 2>/dev/null && "
    "echo DISABLED || echo ALREADY_GONE")
print(out)

# 4. 禁用旧 S99myspireceive（不再需要）
print("\n=== disable old S99myspireceive ===")
out = rk_cmd(s,
    "mv /etc/init.d/S99myspireceive /etc/init.d/S99myspireceive.old 2>/dev/null && "
    "echo DISABLED || echo ALREADY_GONE")
print(out)

# 5. 验证
print("\n=== /etc/init.d/ TOF3 entries ===")
print(rk_cmd(s, "ls /etc/init.d/ | grep -E 'S4[89]|S5[01]|S9[56]'"))

# 6. 测试 stop/start S95（但先不启动，等 USB adapter 就绪）
print("\n=== test S95 status ===")
print(rk_cmd(s, "/etc/init.d/S95tof_spi_receiver status"))

print("\n=== test S96 status ===")
print(rk_cmd(s, "/etc/init.d/S96tof_display status"))

s.close()
print("[done]")
