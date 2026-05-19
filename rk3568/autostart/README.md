# autostart — RK3568 开机自启动（BusyBox init.d）

完整设计见 [`docs/rk3568_framework.md`](../../docs/rk3568_framework.md) §5。

## 方案

Buildroot/BusyBox init.d 风格，仿 legacy `S99myspireceive`：

| 脚本 | 启动 | 阶段 |
|------|------|------|
| `S95tof_spi_receiver` | spi_receiver + Qt 显示程序（实时深度→MIPI 屏） | 本阶段 |
| `S96tof_cloud_syncer` | `python3 cloud_syncer.py`（5G 上传） | ⏸️ 暂缓（P-5G） |

约定：PID 写 `/var/run/`，日志写 `/var/log/`，支持 `start|stop|restart|status`。
spi_receiver 与 Qt 显示进程模型见框架文档 O6（合一或拆分，影响脚本数量）。

参考：`../legacy/RK3568开机自启动代码/`（S99myspireceive、spi_rev_slavemyloop.sh、readme.txt）。

## 状态

⬜ 待 spi_receiver / Qt 显示实现后落地脚本；`S96tof_cloud_syncer` 随 5G 阶段再做。
