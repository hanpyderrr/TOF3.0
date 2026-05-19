# spi_syncer — 哪吒侧实时深度帧 SPI 推送

本阶段 P-RT。把采集层写出的 `TofFrame`（2070B）实时推到 `/dev/spidev1.0`，经 USB转SPI 适配器送 RK3568 显示。

## 角色

```
sim_pf32/ExampleTOF ──写──> /tmp/depth.dat (2070B TofFrame, flock LOCK_EX)
spi_syncer ──按 seq 去重读──> /dev/spidev1.0 (SPI master, MODE0/8bit/1.125MHz)
   └─ USB转SPI 适配器(0483:5740) ─> RK3568 spi_receiver
```

- 传的是**裸 TofFrame**（自带 magic `"TOFP"` + crc16-Modbus），无外层信封（决策见 `docs/realtime_display_plan.md`）。
- 去重按 `TofFrame.seq`（非 mtime），与哪吒 Qt `onTimer` 一致，2fps 不漏不重。
- 实时流：不补传、不 ACK，发送失败仅记日志继续（不阻塞采集，数据已在哪吒本地存档）。
- 独立进程，需 root（spidev）；不改 `nezha/qt_app`。

## 构建与运行（哪吒 x86_64）

```bash
cd nezha/spi_syncer && make
sudo ./spi_syncer                       # 默认 /tmp/depth.dat → /dev/spidev1.0
sudo ./spi_syncer /tmp/depth.dat /dev/spidev1.0   # 显式参数
```

设备名/路径不硬编码，按命令行参数传入。下游接收见 `rk3568/spi_receiver/`。
