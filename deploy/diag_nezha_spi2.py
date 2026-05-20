#!/usr/bin/env python3
"""哪吒 SPI 诊断（不用 sudo）"""
import paramiko, time, sys

HOST = "192.168.31.127"; USER = "ding"; PW = "1234"

def run(ssh, cmd, timeout=8):
    try:
        _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode(errors='replace')
        err = stderr.read().decode(errors='replace')
        return (out + err).strip()
    except Exception as e:
        return f"[timeout/err: {e}]"

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PW, timeout=10)
    print(f"[OK] SSH {HOST}")
except Exception as e:
    print(f"[ERR] {e}"); sys.exit(1)

print("=== /dev/spi* ===")
print(run(ssh, "ls /dev/spi* 2>/dev/null || echo NONE"))

print("\n=== /sys/bus/spi/devices ===")
print(run(ssh, "ls /sys/bus/spi/devices/ 2>/dev/null || echo NONE"))

print("\n=== lsmod | grep spi ===")
print(run(ssh, "lsmod | grep spi"))

print("\n=== SPI platform devices ===")
print(run(ssh, "ls /sys/bus/platform/devices/ | grep -i spi 2>/dev/null || echo NONE"))

print("\n=== /sys/bus/spi/drivers ===")
print(run(ssh, "ls /sys/bus/spi/drivers/ 2>/dev/null"))

print("\n=== dmesg SPI (no sudo) ===")
print(run(ssh, "dmesg 2>/dev/null | grep -i spi | tail -20"))

print("\n=== SPI ko files ===")
print(run(ssh, "find /lib/modules -name 'spi*.ko' 2>/dev/null | head -10"))

print("\n=== /etc/modules and rc.local ===")
print(run(ssh, "cat /etc/modules 2>/dev/null || echo NO_MODULES"))
print(run(ssh, "cat /etc/rc.local 2>/dev/null || echo NO_RCLOCAL"))

print("\n=== ding home files ===")
print(run(ssh, "ls /home/ding/"))

ssh.close()
print("[done]")
