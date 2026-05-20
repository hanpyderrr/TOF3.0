#!/usr/bin/env python3
"""哪吒 SPI 诊断 — 找出如何恢复 spidev1.0"""
import paramiko, time, sys

HOST = "192.168.31.127"; USER = "ding"; PW = "1234"

def run(ssh, cmd, timeout=10):
    _, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode(errors='replace')
    err = stderr.read().decode(errors='replace')
    return (out + err).strip()

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(HOST, username=USER, password=PW, timeout=10)
    print(f"[OK] SSH {HOST}")
except Exception as e:
    print(f"[ERR] {e}"); sys.exit(1)

print("=== 1. SPI 相关设备列表 ===")
print(run(ssh, "ls /dev/spi* 2>/dev/null || echo NONE"))
print(run(ssh, "ls /sys/bus/spi/devices/ 2>/dev/null"))
print(run(ssh, "ls /sys/class/spidev/ 2>/dev/null || echo NO_SPIDEV_CLASS"))

print("\n=== 2. spidev.ko 加载状态 ===")
print(run(ssh, "lsmod | grep spi"))

print("\n=== 3. SPI 主控列表（ACPI/LPSS） ===")
print(run(ssh, "ls /sys/bus/platform/devices/ | grep -i spi"))
print(run(ssh, "ls /sys/bus/spi/drivers/"))

print("\n=== 4. ACPI SPI 节点 ===")
print(run(ssh, "ls /sys/bus/acpi/devices/ | grep -iE 'spi|8086:0ac2|int3443'"))

print("\n=== 5. dmesg SPI 相关 ===")
print(run(ssh, "sudo -S dmesg 2>/dev/null | grep -i spi | tail -30", timeout=15))

print("\n=== 6. 可用 GPIO SPI 信息 ===")
print(run(ssh, "ls /sys/bus/platform/devices/ | grep gpio"))
print(run(ssh, "dmesg 2>/dev/null | grep -i 'gpio\\|spi' | grep -iv 'SPI-NOR\\|spi-nor\\|flash' | tail -20"))

print("\n=== 7. 内核模块（spidev 相关） ===")
print(run(ssh, "find /lib/modules -name 'spidev.ko' 2>/dev/null | head -3"))
print(run(ssh, "find /lib/modules -name 'spi-*.ko' 2>/dev/null | head -10"))

print("\n=== 8. 用户有无自定义 SPI 配置 ===")
print(run(ssh, "ls /home/ding/SPIsend_tsh/ 2>/dev/null || echo GONE"))
print(run(ssh, "ls /home/ding/*.sh /etc/rc.local /etc/modules 2>/dev/null"))

ssh.close()
print("[done]")
