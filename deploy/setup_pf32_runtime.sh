#!/bin/sh
# setup_pf32_runtime.sh — 哪吒上 ExampleTOF 运行所需符号链接（幂等，重启后跑一遍即可）
#
# 背景：1.5.21 PF32 SDK 内部用相对/默认路径找两类资源，
# 当 cwd 不在 SDK 目录时找不到，导致 ExampleTOF 启动失败：
#   1) firmware 默认路径 = ~/Firmware/PF32_USB3.bit
#   2) libPF32_API.so 内部 NEEDED = ../source/OK/Linux_x64/libokFrontPanel.so
#
# 修法：建两个符号链接指到 SDK 真实位置，对任意 cwd 都成立。
#
# 用法（哪吒端）：
#   sh deploy/setup_pf32_runtime.sh        # 默认 SDK 1.5.21
#   PF32_SDK_DIR=/path/to/sdk sh ...        # 覆盖 SDK 根
#
# 与 systemd 关系：tof-acquisition.service 启动 ExampleTOF 前先依赖此初始化；
# 当前 service 的 ExecStart cwd 已落在 ~/tof3-rt/acquisition/，两条符号链接到位即可。

set -eu

SDK_ROOT="${PF32_SDK_DIR:-$HOME/pf32/c++_sample_linux-1.5.21}"
RT_ROOT="${TOF3_RT_DIR:-$HOME/tof3-rt}"

FW_SRC="$SDK_ROOT/Firmware"
FW_LINK="$HOME/Firmware"

SRC_SRC="$SDK_ROOT/PhotonForce/source"
SRC_LINK="$RT_ROOT/source"

ensure_symlink() {
    target="$1"; link="$2"
    if [ ! -e "$target" ]; then
        echo "[setup_pf32_runtime] FATAL: target missing: $target"
        exit 2
    fi
    if [ -L "$link" ]; then
        cur="$(readlink "$link")"
        if [ "$cur" = "$target" ]; then
            echo "[setup_pf32_runtime] OK   $link -> $target"
            return 0
        fi
        echo "[setup_pf32_runtime] REL  $link (was -> $cur) -> $target"
        ln -sfn "$target" "$link"
        return 0
    fi
    if [ -e "$link" ]; then
        echo "[setup_pf32_runtime] FATAL: $link exists and is not a symlink, refuse to overwrite"
        exit 3
    fi
    echo "[setup_pf32_runtime] NEW  $link -> $target"
    ln -s "$target" "$link"
}

mkdir -p "$RT_ROOT"
ensure_symlink "$FW_SRC"  "$FW_LINK"
ensure_symlink "$SRC_SRC" "$SRC_LINK"

# 最终自检：从默认 cwd 出发能 resolve 到真实文件
test -f "$FW_LINK/PF32_USB3.bit" \
    && echo "[setup_pf32_runtime] firmware reachable: $FW_LINK/PF32_USB3.bit" \
    || { echo "[setup_pf32_runtime] FATAL: PF32_USB3.bit not reachable via $FW_LINK"; exit 4; }

OK_REL="$RT_ROOT/acquisition/../source/OK/Linux_x64/libokFrontPanel.so"
test -f "$OK_REL" \
    && echo "[setup_pf32_runtime] okFrontPanel reachable from acquisition/: $OK_REL" \
    || { echo "[setup_pf32_runtime] FATAL: libokFrontPanel.so not reachable via $OK_REL"; exit 5; }

echo "[setup_pf32_runtime] done."
