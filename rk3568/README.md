# RK3568 侧

RK3568 定位：**实时深度显示终端 + 镜头电机控制器 +（日后）5G 上行网关**。不做算法（哪吒负责）。

完整设计见 **[`docs/rk3568_framework.md`](../docs/rk3568_framework.md)**。

## 模块

| 目录 | 职责 | 语言 | 状态 |
|------|------|------|------|
| `spi_receiver/` | USB转SPI 适配器做 slave，收哪吒实时二进制深度帧 | C（交叉编译 aarch64） | ⬜ 本阶段新写 |
| `qt_display/`（待建） | 深度帧 → MIPI 屏实时渲染 → 即弃 | C++/Qt（交叉编译） | ⬜ 本阶段新写 |
| `motor_controller/` | 串口 → STM32 → TMC2209 镜头调焦/光圈 | Python 3.8 | ⬜ 待实现 |
| `cloud_syncer/` | 扫描 buffer，5G POST 云端 FastAPI | Python 3.8 | ✅ 已实现+e2e；**归暂缓阶段，保留不动** |
| `autostart/` | BusyBox init.d 开机自启动 | shell | ⬜ 待实现 |
| `legacy/` | v1.0 遗留代码（含 RK3568 上的 Qt 显示参考），**只读** | — | 参考 |

## 已锁定决策

- **RK3568 实时 Qt MIPI 屏显深度图**（硬需求；v1.0 已在板上跑过 Qt 显示）
- 深度帧走 **SPI 实时流**（二进制 TofFrame 2KB）；原始 TCSPC 只哪吒本地存
- SPI 接收走 **USB转SPI 适配器**（非原生 SPI），物理链路已实测通
- 电机 **RK3568 直连 STM32 串口**（非经 SPI CMD=0x06）
- **5G 上云本阶段暂缓**；`cloud_syncer` 已就绪，日后直接接
- 板上无 gcc：C/Qt 交叉编译，逻辑层 Python 3.8
