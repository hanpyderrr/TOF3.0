#!/usr/bin/env bash
#
# Nezha/N97 spidev diagnostic and recovery helper.
# Run on Nezha:
#   sudo bash deploy/setup_spidev.sh
# Optional:
#   sudo SPI_BUS=1 SPI_CS=0 bash deploy/setup_spidev.sh
#
set -u

SPI_BUS="${SPI_BUS:-}"
SPI_CS="${SPI_CS:-0}"
SPI_MODALIAS="${SPI_MODALIAS:-spidev}"
DRIVER_BIND="/sys/bus/spi/drivers/spidev/bind"
DRIVER_OVERRIDE_NAME="driver_override"

log() { printf '[setup_spidev] %s\n' "$*"; }
warn() { printf '[setup_spidev][WARN] %s\n' "$*" >&2; }
die() { printf '[setup_spidev][ERROR] %s\n' "$*" >&2; exit 1; }

need_root_for_write() {
    if [ "$(id -u)" -ne 0 ]; then
        die "binding spidev requires root; rerun with sudo"
    fi
}

show_cmd() {
    log "$ $*"
    "$@" 2>&1 | sed 's/^/  /' || true
}

list_spidev_nodes() {
    if ls /dev/spidev* >/dev/null 2>&1; then
        ls -l /dev/spidev*
        return 0
    fi
    return 1
}

print_diagnostics() {
    log "kernel: $(uname -a)"
    log "checking loaded SPI/spidev modules"
    show_cmd lsmod

    if command -v lspci >/dev/null 2>&1; then
        log "PCI LPSS/SPI candidates"
        lspci -nn | grep -Ei 'spi|serial bus|lpss|intel' | sed 's/^/  /' || true
    fi

    log "ACPI SPI/LPSS candidates"
    find /sys/bus/acpi/devices -maxdepth 2 -type f \( -name hid -o -name path -o -name status \) 2>/dev/null |
        while read -r f; do
            v="$(cat "$f" 2>/dev/null || true)"
            case "$v" in
                *SPI*|*spi*|INT33C1|INT3430|INT3440|80860F0E|8086228E|INTC10*|INTC11*)
                    printf '  %s: %s\n' "$f" "$v"
                    ;;
            esac
        done

    log "platform SPI controller candidates"
    find /sys/bus/platform/devices -maxdepth 1 -type l 2>/dev/null |
        grep -Ei 'spi|pxa2xx|lpss|intel' | sed 's/^/  /' || true

    log "registered SPI masters"
    find /sys/class/spi_master -maxdepth 1 -type l -printf '  %f -> %l\n' 2>/dev/null || true

    log "registered SPI devices"
    find /sys/bus/spi/devices -maxdepth 1 -type l -printf '  %f -> %l\n' 2>/dev/null || true
}

load_modules() {
    log "loading spidev and common Intel LPSS SPI modules"
    for m in spidev spi_pxa2xx_platform intel_lpss intel_lpss_pci intel_lpss_acpi; do
        modprobe "$m" 2>/dev/null && log "modprobe $m ok" || warn "modprobe $m failed or unavailable"
    done
}

bind_existing_spi_devices() {
    local changed=0
    [ -e "$DRIVER_BIND" ] || return 0

    for dev_path in /sys/bus/spi/devices/spi*.*; do
        [ -e "$dev_path" ] || continue
        dev="$(basename "$dev_path")"
        if [ -e "$dev_path/driver" ]; then
            log "$dev already has driver: $(basename "$(readlink "$dev_path/driver")")"
            continue
        fi

        need_root_for_write
        log "binding existing SPI device $dev to spidev"
        if [ -w "$dev_path/$DRIVER_OVERRIDE_NAME" ]; then
            printf '%s' "$SPI_MODALIAS" > "$dev_path/$DRIVER_OVERRIDE_NAME" || true
        fi
        printf '%s' "$dev" > "$DRIVER_BIND" || warn "bind failed for $dev"
        changed=1
    done
    return "$changed"
}

new_device_name_for_master() {
    local master="$1"
    printf 'spidev %s\n' "$SPI_CS" > "/sys/class/spi_master/$master/new_device"
}

create_spidev_on_masters() {
    local created=0
    [ -e /sys/class/spi_master ] || return 0

    for master_path in /sys/class/spi_master/spi*; do
        [ -e "$master_path" ] || continue
        master="$(basename "$master_path")"
        bus="${master#spi}"
        if [ -n "$SPI_BUS" ] && [ "$bus" != "$SPI_BUS" ]; then
            continue
        fi

        if [ -e "/sys/bus/spi/devices/spi${bus}.${SPI_CS}" ]; then
            log "spi${bus}.${SPI_CS} already exists"
            continue
        fi

        if [ ! -w "$master_path/new_device" ]; then
            need_root_for_write
        fi

        log "creating spidev device on ${master}.${SPI_CS}"
        new_device_name_for_master "$master" || warn "new_device failed for ${master}.${SPI_CS}"
        created=1
    done
    return "$created"
}

main() {
    print_diagnostics

    if list_spidev_nodes; then
        log "spidev node(s) already available"
        exit 0
    fi

    load_modules
    if list_spidev_nodes; then
        log "spidev node(s) appeared after modprobe"
        exit 0
    fi

    bind_existing_spi_devices || true
    if list_spidev_nodes; then
        log "spidev node(s) available after binding existing SPI devices"
        exit 0
    fi

    create_spidev_on_masters || true
    bind_existing_spi_devices || true
    if list_spidev_nodes; then
        log "spidev node(s) available after sysfs new_device/bind"
        exit 0
    fi

    warn "no /dev/spidev* node found"
    warn "If no spi_master exists, enable the LPSS/SPI controller in BIOS/ACPI or kernel config."
    exit 2
}

main "$@"
