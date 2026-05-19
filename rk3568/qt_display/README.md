# qt_display — RK3568 MIPI 屏实时深度图（本阶段核心）

实施计划见 [`docs/realtime_display_plan.md`](../../docs/realtime_display_plan.md)。

## 职责

定时读 `spi_receiver` 写出的 `received.dat`（裸 TofFrame 2070B），按 `seq` 去重，
`DepthParser` 校验解析 → `DepthWidget` jet 伪彩渲染 → 铺满 MIPI 屏（板子 800×1280 竖屏）。
**文件桥**：与 spi_receiver 经 `/tmp/received.dat`（tmpfs）解耦。

## 文件

| 文件 | 来源 |
|------|------|
| `depthParser.{cpp,h}`、`depthWidget.{cpp,h}`、`tof_frame_parser_core.h` | 原样移植自 `单光子项目/TOF/RK3568端/`（已协议对齐，勿改协议字段）|
| `main.cpp`、`mainwindow.{cpp,h}` | 精简重写（仿 legacy `SinglePhoton207_5` 骨架，**剔除**云/课题2/转台/电机/文本 image）|
| `qt_display.pro` | `QT += core gui widgets`（无 network/serialport/opengl/zlib）|

## 构建（板上无 gcc，用 SDK qmake 交叉编译）

```bash
SDK=~/rk3568_linux_sdk/buildroot/output/rockchip_rk3568
mkdir -p build && cd build
$SDK/host/bin/qmake ../qt_display.pro && make -j4
```

产物 `qt_display`（aarch64，链 Qt5.15.2，板上 Qt 库齐全）经串口 base64 传板上
`/myApp/tof3/qt_display/`。

## 运行

```bash
./qt_display [received_dat_path]      # 默认 /tmp/received.dat
```

平台沿用 legacy `SinglePhoton207_5` 启动环境（不显式设 `QT_QPA_PLATFORM`）；
自启见 `rk3568/autostart/S96tof_display`。

## 状态

✅ 已实现，SDK qmake 交叉编译通过（aarch64，Qt5.15.2，无报错/警告）。
⬜ 板上联调（屏显效果、竖屏取向、平台插件）待硬件接入。
