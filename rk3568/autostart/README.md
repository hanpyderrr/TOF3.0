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

## 状态

✅ `S95tof_spi_receiver` / `S96tof_display` 已落地（部署路径 `/myApp/tof3/{spi_receiver,qt_display}/`）。
⬜ 板上装载验证待硬件联调；`S96tof_cloud_syncer` 随 5G 阶段再做。
