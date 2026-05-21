# autostart — RK3568 开机自启动（BusyBox init.d）

完整设计见 [`docs/rk3568_framework.md`](../../docs/rk3568_framework.md) §5。

## 方案

Buildroot/BusyBox init.d 风格，仿 legacy `S99myspireceive`：

| 脚本 | 启动 | 阶段 |
|------|------|------|
| `S95tof_spi_receiver` | `spi_receiver` → `/tmp/received.dat`（裸 TofFrame）| ✅ 本阶段 |
| `S96tof_display` | `qt_display`（读 received.dat → MIPI 屏），在 S95 之后 | ✅ 本阶段 |
| ~~`S96tof_cloud_syncer`~~ | `python3 cloud_syncer.py`（5G 上传）| ⏸️ 暂缓（P-5G）|

约定：PID 写 `/var/run/`，日志写 `/var/log/`，支持 `start|stop|restart|status`。
进程模型 = **文件桥**（O6 已定）：spi_receiver / qt_display 两进程经 `/tmp/received.dat`(tmpfs) 解耦，故两个脚本，S95 先于 S96。

参考：`../legacy/RK3568开机自启动代码/`（S99myspireceive、spi_rev_slavemyloop.sh、readme.txt）。

## 禁用旧 v1.0 自启（必须）

旧单光子 v1.0 的 `S51mydisplay`（拉起 `/myApp/mytest/qttest/SinglePhoton207_5`）和 `S99myspireceive` 与本版冲突，会抢屏/抢 USB-SPI 适配器，必须禁用。

⚠️ **改成 `.old` 后缀禁不掉**：Buildroot `/etc/init.d/rcS` 用 `for i in /etc/init.d/S??*` 遍历，`S51mydisplay.old` 仍以 `S` 开头、仍匹配 `S??*`，照样被 `$i start` 启动。表现为开机三阶段闪屏（旧界面→qt 兜底→真实图）。

正确做法 —— 改成**不以 S 开头**的名字（板上，root）：

```sh
mv /etc/init.d/S51mydisplay.old    /etc/init.d/DISABLED.mydisplay
mv /etc/init.d/S99myspireceive.old /etc/init.d/DISABLED.myspireceive
```

## 状态

✅ `S95tof_spi_receiver` / `S96tof_display` 已落地并装载验证（部署路径 `/myApp/tof3/{spi_receiver,qt_display}/`），重启后屏显实时深度图正常。
✅ 旧 `S51mydisplay`/`S99myspireceive` 已改名 `DISABLED.*` 真正禁用（2026-05-21）。
⬜ `S96tof_cloud_syncer` 随 5G 阶段再做。
