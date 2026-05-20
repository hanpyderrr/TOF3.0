#!/usr/bin/env python3
"""
解耦显示测试：
  1. 重启 weston
  2. 生成合法 TofFrame → 写 /tmp/received.dat（通过 base64 串口传输）
  3. 启动 TOF3.0 qt_display，捕获 30s 日志
"""
import serial, time, sys, struct, base64

COM  = "COM7"
BAUD = 1500000

# ─── TofFrame 生成 ─────────────────────────────────────────────────────────
MAGIC    = 0x50464F54  # "TOFP" LE
VERSION  = 1
HDR_SIZE = 16
WIDTH    = 32
HEIGHT   = 32
PIXELS   = WIDTH * HEIGHT
FRAME_SZ = 2070

def crc16_modbus(data: bytes) -> int:
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if (crc & 1) else crc >> 1
    return crc & 0xFFFF

def make_frame(seq: int = 1) -> bytes:
    """生成深度从 100mm(左上) 到 8000mm(右下) 渐变的合法帧"""
    buf = bytearray(FRAME_SZ)
    # header
    struct.pack_into('<I', buf, 0, MAGIC)
    buf[4] = VERSION
    buf[5] = HDR_SIZE
    struct.pack_into('<I', buf, 8, seq)
    struct.pack_into('<H', buf, 12, WIDTH)
    struct.pack_into('<H', buf, 14, HEIGHT)
    # depths: 渐变色，便于肉眼判断渲染是否正常
    valid = 0
    for i in range(PIXELS):
        d = int(100 + (8000 - 100) * i / (PIXELS - 1))
        struct.pack_into('<H', buf, 20 + i * 2, d)
        valid += 1
    struct.pack_into('<H', buf, 16, valid)
    # CRC over buf[4 .. 2067] (2064 bytes)
    crc = crc16_modbus(bytes(buf[4:FRAME_SZ - 2]))
    struct.pack_into('<H', buf, FRAME_SZ - 2, crc)
    return bytes(buf)

# ─── 串口工具 ──────────────────────────────────────────────────────────────
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

def send_cmd_slow(s, cmd, wait=3.0):
    """长命令用 1-byte/块 写入"""
    s.reset_input_buffer()
    slow_write(s, b'\x15')
    time.sleep(0.05)
    # 逐字节写，每字节 6ms
    for b in (cmd + '\n').encode():
        s.write(bytes([b]))
        time.sleep(0.006)
    time.sleep(wait)
    return s.read(s.in_waiting).decode(errors='replace')

# ─── 主流程 ───────────────────────────────────────────────────────────────
def main():
    try:
        s = serial.Serial(COM, BAUD, timeout=0.5)
        s.dtr = False
        time.sleep(0.3)
        print(f"[OK] {COM} @ {BAUD}")
    except Exception as e:
        print(f"[ERR] open serial: {e}"); sys.exit(1)

    # ── Step 0: 杀掉残留进程 ──────────────────────────────────────────
    print("\n── Step 0: kill stale processes ──")
    print(send_cmd(s, "killall weston qt_display 2>/dev/null ; rm -f /var/run/wayland-0 ; echo KILLED"))

    time.sleep(0.5)

    # ── Step 1: 启 weston ─────────────────────────────────────────────
    print("\n── Step 1: start weston ──")
    print(send_cmd(s, ". /etc/profile && /usr/bin/weston > /tmp/weston.log 2>&1 &"))
    time.sleep(3)

    # 等 wayland-0
    for i in range(10):
        out = send_cmd(s, "ls /var/run/wayland-0 2>/dev/null && echo WESTON_UP || echo WESTON_WAIT", wait=1.0)
        if 'WESTON_UP' in out:
            print(f"  weston up after {i+1}s"); break
        print(f"  waiting... ({i+1})")
        time.sleep(1)
    else:
        print("[WARN] wayland-0 still not found, continue anyway")

    # ── Step 2: 写 received.dat ───────────────────────────────────────
    print("\n── Step 2: write synthetic received.dat ──")
    frame = make_frame(seq=1)
    b64 = base64.b64encode(frame).decode()
    print(f"  frame size = {len(frame)} bytes, b64 len = {len(b64)}")

    # 分段写：每段 60 字符，避免命令行过长
    CHUNK = 60
    # 先清空
    print(send_cmd(s, "rm -f /tmp/received.dat /tmp/frame.b64 && echo CLEARED"))
    # 分段 append 到 /tmp/frame.b64
    for i in range(0, len(b64), CHUNK):
        seg = b64[i:i+CHUNK]
        cmd = f"printf '%s' '{seg}' >> /tmp/frame.b64"
        send_cmd(s, cmd, wait=0.3)
    print(f"  b64 written ({len(b64)} chars in {(len(b64)+CHUNK-1)//CHUNK} chunks)")
    # 解码
    print(send_cmd(s, "base64 -d /tmp/frame.b64 > /tmp/received.dat && ls -la /tmp/received.dat"))

    # 验证大小
    out = send_cmd(s, "wc -c /tmp/received.dat")
    print(f"  size check: {out.strip()}")

    # ── Step 3: 起 qt_display ─────────────────────────────────────────
    print("\n── Step 3: start qt_display ──")
    print(send_cmd(s, "rm -f /tmp/qt.log"))
    cmd = ". /etc/profile && /myApp/tof3/qt_display/qt_display /tmp/received.dat > /tmp/qt.log 2>&1 &"
    print(send_cmd(s, cmd, wait=2.0))

    # 等 3s 拿日志
    time.sleep(3)
    print("\n── Step 4: qt_display log (first 60 lines) ──")
    print(send_cmd(s, "cat /tmp/qt.log", wait=2.0))

    # 查进程是否还在
    print("\n── Step 5: process check ──")
    print(send_cmd(s, "ps | grep -E 'weston|qt_disp'"))

    s.close()
    print("[done]")

if __name__ == "__main__":
    main()
