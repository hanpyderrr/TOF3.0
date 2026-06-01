#!/bin/sh
# tof_spi_watchdog.sh — 监控 /tmp/received.dat 更新；停滞 > 60s 触发 S95 restart
#
# 部署位置：/usr/bin/tof_spi_watchdog.sh（chmod +x）
# Buildroot 默认无 /usr/local/，故用 /usr/bin/
# 由 /etc/init.d/S97tof_spi_watchdog 在开机时拉起为后台进程
#
# 兜底场景：USB-SPI 适配器 device renumber 后 spi_receiver 死循环 OpenUsb=-1，
# /tmp/received.dat 不再更新。watchdog 检测到停滞，重启 S95 让 spi_receiver
# 重新拿到当前 USB device。autosuspend 已由 udev rule 关闭，watchdog 是"二道关"。
#
# 设计：
#   - 30s 周期，比 stall 阈值小 2 倍避免漏检
#   - stall > 60s 触发 restart
#   - 连续 restart 之间至少 90s cooldown，避免链路恢复期内反复杀
#   - 所有事件 + S95 输出落 /var/log/tof_spi_watchdog.log（systemd 不管 init.d，自己管日志）

set -u

RECEIVED=/tmp/received.dat
STALL_LIMIT=60
POLL=30
COOLDOWN=90
LOG=/var/log/tof_spi_watchdog.log

last_restart=0

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG"
}

log "watchdog started (poll=${POLL}s stall=${STALL_LIMIT}s cooldown=${COOLDOWN}s)"

while true; do
    now=$(date +%s)

    if [ ! -f "$RECEIVED" ]; then
        # 文件还没出现（spi_receiver 刚启动）—— 不算 stall，等下一轮
        sleep "$POLL"
        continue
    fi

    # BusyBox stat 用 -c %Y（与 GNU 一致）
    mtime=$(stat -c %Y "$RECEIVED" 2>/dev/null)
    if [ -z "$mtime" ]; then
        log "warn: stat failed on $RECEIVED"
        sleep "$POLL"
        continue
    fi

    stall=$((now - mtime))
    if [ "$stall" -gt "$STALL_LIMIT" ]; then
        since_last=$((now - last_restart))
        if [ "$since_last" -gt "$COOLDOWN" ]; then
            log "stall=${stall}s > ${STALL_LIMIT}s, restarting S95tof_spi_receiver"
            /etc/init.d/S95tof_spi_receiver restart >> "$LOG" 2>&1
            last_restart=$now
        else
            log "stall=${stall}s but in cooldown (${since_last}s/${COOLDOWN}s)"
        fi
    fi

    sleep "$POLL"
done
