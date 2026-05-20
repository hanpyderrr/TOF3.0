#!/usr/bin/env python3
"""
e2e_test.py — TOF3.0 全链路端到端测试
Windows 运行；依赖 paramiko + pyserial

测试链路：哪吒 sim_pf32 → spi_syncer → RK3568 spi_receiver → /tmp/received.dat → qt_display

用法：
    python deploy/e2e_test.py
    python deploy/e2e_test.py --no-spi   # 跳过 SPI（spidev1.0 缺失时仅测显示）
"""
import argparse, sys, time, struct
import paramiko
import serial

# ── 配置 ─────────────────────────────────────────────────────────────────────
NEZHA_HOST = "192.168.31.127"
NEZHA_USER = "ding"
NEZHA_PASS = "1234"

RK_COM  = "COM7"
RK_BAUD = 1500000

POLL_SECS    = 40   # 等待 received.dat 更新的最长秒数
POLL_INTERVAL = 2
# ─────────────────────────────────────────────────────────────────────────────

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)

# ── 串口工具（CH340 1.5Mbaud 慢写） ──────────────────────────────────────────
def slow_write(s, data, delay=0.006):
    for i in range(0, len(data), 3):
        s.write(data[i:i+3])
        time.sleep(delay)

def rk_cmd(s, cmd, wait=2.0):
    s.reset_input_buffer()
    slow_write(s, b'\x15')
    time.sleep(0.05)
    slow_write(s, (cmd + '\n').encode())
    time.sleep(wait)
    return s.read(s.in_waiting).decode(errors='replace')

# ── SSH 工具 ──────────────────────────────────────────────────────────────────
def ssh_run(ssh, cmd, timeout=15):
    try:
        _, out, err = ssh.exec_command(cmd, timeout=timeout)
        return (out.read() + err.read()).decode(errors='replace').strip()
    except Exception as e:
        return f"[ssh error: {e}]"

# ── TofFrame 生成（用于合成 received.dat 的 fallback） ───────────────────────
def crc16_modbus(data):
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if (crc & 1) else crc >> 1
    return crc & 0xFFFF

def make_frame(seq=1):
    FRAME_SZ = 2070
    buf = bytearray(FRAME_SZ)
    struct.pack_into('<I', buf, 0, 0x50464F54)  # magic "TOFP"
    buf[4] = 1   # version
    buf[5] = 16  # header_size
    struct.pack_into('<I', buf, 8, seq)
    struct.pack_into('<H', buf, 12, 32)  # width
    struct.pack_into('<H', buf, 14, 32)  # height
    valid = 0
    for i in range(1024):
        d = int(100 + (8000 - 100) * i / 1023)
        struct.pack_into('<H', buf, 20 + i * 2, d)
        valid += 1
    struct.pack_into('<H', buf, 16, valid)
    crc = crc16_modbus(bytes(buf[4:FRAME_SZ - 2]))
    struct.pack_into('<H', buf, FRAME_SZ - 2, crc)
    return bytes(buf)

def upload_synthetic_frame(rk):
    """将合成帧通过 base64 传入 RK3568 /tmp/received.dat"""
    import base64
    frame = make_frame(seq=1)
    b64 = base64.b64encode(frame).decode()
    rk_cmd(rk, "rm -f /tmp/frame.b64 /tmp/received.dat", wait=0.5)
    CHUNK = 60
    for i in range(0, len(b64), CHUNK):
        rk_cmd(rk, f"printf '%s' '{b64[i:i+CHUNK]}' >> /tmp/frame.b64", wait=0.2)
    rk_cmd(rk, "base64 -d /tmp/frame.b64 > /tmp/received.dat", wait=1.0)
    out = rk_cmd(rk, "wc -c /tmp/received.dat")
    log(f"  synthetic received.dat: {out.strip()}")

# ── 主测试流程 ────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-spi", action="store_true", help="skip SPI (no spidev1.0)")
    parser.add_argument("--display-only", action="store_true", help="only test display with synthetic frame")
    args = parser.parse_args()

    results = {}

    # ── 1. 连接哪吒 ────────────────────────────────────────────────────────
    log("=== connecting to Nezha ===")
    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(NEZHA_HOST, username=NEZHA_USER, password=NEZHA_PASS, timeout=10)
        log(f"  SSH OK: {NEZHA_HOST}")
    except Exception as e:
        log(f"  SSH FAIL: {e}")
        ssh = None

    # ── 2. 连接 RK3568 ────────────────────────────────────────────────────
    log("=== connecting to RK3568 ===")
    try:
        rk = serial.Serial(RK_COM, RK_BAUD, timeout=0.5)
        rk.dtr = False
        time.sleep(0.3)
        log(f"  serial OK: {RK_COM}")
    except Exception as e:
        log(f"  serial FAIL: {e}")
        rk = None

    # ── 3. 哪吒：检查 spidev1.0 ───────────────────────────────────────────
    if ssh:
        log("=== Nezha: check spidev1.0 ===")
        spidev = ssh_run(ssh, "ls /dev/spidev1.0 2>/dev/null && echo OK || echo MISSING")
        log(f"  spidev1.0: {spidev}")
        results["spidev"] = "OK" in spidev

        depth = ssh_run(ssh, "ls -la /tmp/depth.dat 2>/dev/null || echo MISSING")
        log(f"  depth.dat: {depth}")

    # ── 4. 哪吒：启 sim_pf32 ─────────────────────────────────────────────
    if ssh and not args.display_only:
        log("=== Nezha: start sim_pf32 ===")
        ssh_run(ssh, "killall sim_pf32 spi_syncer 2>/dev/null; sleep 0.5", timeout=5)
        ssh_run(ssh, (
            "nohup /home/ding/TOF3.0/nezha/acquisition/sim_pf32 "
            "> /tmp/sim_pf32.log 2>&1 & echo $!"
        ), timeout=5)
        time.sleep(2)
        sz = ssh_run(ssh, "stat -c %s /tmp/depth.dat 2>/dev/null || echo 0")
        log(f"  depth.dat size after 2s: {sz.strip()} bytes")
        results["sim_pf32"] = sz.strip() not in ("0", "")

    # ── 5. RK3568：USB adapter reset + spi_receiver ───────────────────────
    if rk and not args.display_only:
        log("=== RK3568: USB reset + spi_receiver ===")
        out = rk_cmd(rk,
            "echo 2-1 > /sys/bus/usb/drivers/usb/unbind 2>/dev/null; "
            "sleep 1; echo 2-1 > /sys/bus/usb/drivers/usb/bind 2>/dev/null; "
            "sleep 1; echo USB_RESET_DONE",
            wait=3.5)
        log(f"  USB reset: {'OK' if 'USB_RESET_DONE' in out else 'no output'}")

        rk_cmd(rk, "killall spi_receiver 2>/dev/null; sleep 0.3", wait=0.5)
        out = rk_cmd(rk,
            "/myApp/tof3/spi_receiver/spi_receiver /tmp/received.dat "
            "> /var/log/spi_receiver.log 2>&1 & echo SPI_RX_STARTED",
            wait=1.5)
        log(f"  spi_receiver: {'started' if 'SPI_RX_STARTED' in out else out.strip()[:80]}")

    # ── 6. 哪吒：启 spi_syncer（若 spidev1.0 存在）───────────────────────
    if ssh and results.get("spidev") and not args.display_only and not args.no_spi:
        log("=== Nezha: start spi_syncer ===")
        out = ssh_run(ssh, (
            "echo 1234 | sudo -S "
            "nohup /home/ding/TOF3.0/nezha/spi_syncer/spi_syncer "
            "> /tmp/spi_syncer.log 2>&1 & echo SPI_TX_STARTED"
        ), timeout=10)
        log(f"  spi_syncer: {out.strip()[:80]}")
        time.sleep(1)
    elif not results.get("spidev") and not args.no_spi and not args.display_only:
        log("  spidev1.0 missing — skipping spi_syncer; use --no-spi to suppress this warning")

    # ── 7. 如果纯显示测试：写合成帧 ──────────────────────────────────────
    if args.display_only and rk:
        log("=== RK3568: upload synthetic frame (display-only mode) ===")
        upload_synthetic_frame(rk)

    # ── 8. 轮询 received.dat mtime ────────────────────────────────────────
    if rk and not args.display_only:
        log(f"=== polling received.dat for {POLL_SECS}s ===")
        prev_mtime = None
        deadline = time.time() + POLL_SECS
        while time.time() < deadline:
            out = rk_cmd(rk, "stat -c %Y /tmp/received.dat 2>/dev/null || echo 0", wait=1.0)
            mtime_str = out.strip().split()[-1] if out.strip() else "0"
            try:
                mtime = int(mtime_str)
            except ValueError:
                mtime = 0

            if mtime != 0 and mtime != prev_mtime:
                if prev_mtime is not None:
                    log(f"  received.dat updated! mtime={mtime}")
                    results["received_dat"] = True
                    break
                prev_mtime = mtime
                log(f"  received.dat exists (mtime={mtime}), waiting for update...")
            elif mtime == 0:
                log("  received.dat not yet created...")

            time.sleep(POLL_INTERVAL)
        else:
            log("  TIMEOUT: received.dat not updated within window")
            results["received_dat"] = False

    # ── 9. RK3568：检查 qt_display ───────────────────────────────────────
    if rk:
        log("=== RK3568: check qt_display ===")
        out = rk_cmd(rk, "ps | grep qt_disp | grep -v grep || echo NOT_RUNNING", wait=1.0)
        running = "NOT_RUNNING" not in out
        log(f"  qt_display: {'running' if running else 'NOT running'}")
        results["qt_display"] = running
        if not running:
            log("  → start qt_display")
            rk_cmd(rk,
                ". /etc/profile && /myApp/tof3/qt_display/qt_display "
                "/tmp/received.dat > /var/log/qt_display.log 2>&1 &",
                wait=1.5)

    # ── 10. 日志收尾 ──────────────────────────────────────────────────────
    log("=== logs ===")
    if ssh:
        log("Nezha sim_pf32 (last 5):")
        print(ssh_run(ssh, "tail -5 /tmp/sim_pf32.log 2>/dev/null || echo (empty)"))
        if results.get("spidev"):
            log("Nezha spi_syncer (last 5):")
            print(ssh_run(ssh, "tail -5 /tmp/spi_syncer.log 2>/dev/null || echo (empty)"))

    if rk:
        log("RK3568 spi_receiver (last 5):")
        print(rk_cmd(rk, "tail -5 /var/log/spi_receiver.log 2>/dev/null || echo (empty)", wait=1.5))

    # ── 结果 ─────────────────────────────────────────────────────────────
    log("=== RESULTS ===")
    all_pass = True
    for k, v in results.items():
        status = "PASS" if v else "FAIL"
        if not v:
            all_pass = False
        log(f"  {k}: {status}")

    if all_pass:
        log("OVERALL: PASS")
    else:
        log("OVERALL: FAIL — see above for failing items")

    if ssh:
        ssh.close()
    if rk:
        rk.close()

    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
