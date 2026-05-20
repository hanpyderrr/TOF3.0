#!/usr/bin/env python3
"""步骤1：上传并运行 setup_spidev.sh 到哪吒"""
import paramiko, time, sys

HOST = "192.168.31.127"; USER = "ding"; PW = "1234"

def run(ssh, cmd, timeout=12):
    try:
        _, out, err = ssh.exec_command(cmd, timeout=timeout)
        return (out.read() + err.read()).decode(errors='replace').strip()
    except Exception as e:
        return f"[err: {e}]"

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PW, timeout=8)
    print(f"[OK] SSH {HOST}")
except Exception as e:
    print(f"[ERR] SSH: {e}"); sys.exit(1)

# 上传 setup_spidev.sh
sftp = ssh.open_sftp()
local = r"E:\vs-workspace\TOF3.0\deploy\setup_spidev.sh"
remote = "/home/ding/setup_spidev.sh"
sftp.put(local, remote)
sftp.chmod(remote, 0o755)
sftp.close()
print(f"[OK] uploaded → {remote}")

# 运行（不带 sudo，先看诊断部分）
print("\n=== 诊断 SPI（非 root 部分）===")
out = run(ssh, f"bash {remote} 2>&1", timeout=30)
print(out)

print("\n=== /dev/spidev* ===")
print(run(ssh, "ls /dev/spidev* 2>/dev/null || echo NONE"))

print("\n=== spi_master 列表 ===")
print(run(ssh, "ls /sys/class/spi_master/ 2>/dev/null || echo NONE"))

ssh.close()
print("[done]")
