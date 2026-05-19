# RK3568 侧框架设计

> 版本：2026-05-19（按已锁定决策重写）
> 状态：框架定稿，代码实现待 P-RT 阶段
> 关联：`ARCHITECTURE.md`、`docs/spi硬件接口.md`、`docs/agent-work/progress.md`

---

## 0. 已锁定决策（本框架前提）

| 决策 | 结论 | 否决/暂缓的方案 |
|------|------|-----------|
| RK3568 是否做显示 | **做：实时 Qt MIPI 屏显深度图**（v1.0 单光子已在 RK3568 跑过 Qt 显示） | 旧"RK3568 不做显示"作废 |
| 深度帧传输 | **SPI 实时流**（TofFrame 2KB/帧，低延迟） | 旧"纯文件队列异步、不做实时流"作废（那是为 2MB 原始定的） |
| 原始 TCSPC | **只哪吒本地存档**，不过 SPI/5G | 全量自动上云（SPI ~50–140KB/s 物理不可行） |
| 5G 上云 | **本阶段暂缓**，日后稳定再加 | `cloud_syncer` 已实现+e2e 过，保留不动归暂缓阶段 |
| SPI 接收方案 | **USB转SPI 适配器**做 slave（USB 0483:5740，物理链路实测通） | RK3568 原生 SPI slave（设备树 fe620000 被 STM32 占、其余 disabled） |
| 电机控制归属 | **RK3568 直连 STM32 串口**（19200 8N1） | 经 SPI CMD=0x06；留哪吒 |

> 早期 `docs/rk3568_reintegration_architecture.md` 仅留档。本文与 `ARCHITECTURE.md`、`CLAUDE.md` 一致。

---

## 1. RK3568 在系统中的角色

```
哪吒 NUC（生产无网，采集+算法+激光闭环+本地全量存档 raw+depth）
   │  实时深度流：TofFrame(2KB) 低延迟 → /dev/spidev1.0 SPI master MODE0 1.125MHz
   ▼
USB转SPI 适配器（0483:5740）── USB ──►  RK3568（aarch64, Buildroot, Qt+MIPI 屏, 5G）
                                   ├── spi_receiver      收二进制深度帧
                                   ├── Qt 显示程序        深度帧 → MIPI 屏实时渲染 → 即弃
                                   ├── motor_controller   串口 → STM32 → TMC2209 → 镜头
                                   └──【暂缓】cloud_syncer + net_manager  5G → 公网云
```

RK3568 定位：**实时深度显示终端 + 镜头电机控制器 +（日后）5G 上行网关**。不做算法（哪吒负责）。

---

## 2. 目录结构（TOF3.0/rk3568/）

```
rk3568/
├── README.md                  本侧总览，指向本框架文档
├── legacy/                    v1.0 遗留代码（只读参考，勿改）
│   ├── RK3568使用SPI接收数据代码/   spi_rev_slavemyloop0411.c（传输层参考）
│   ├── 客户端代码/SinglePhoton207_5/ 旧 Qt（RK3568 上的 Qt+显示参考）
│   ├── 服务器代码/                 旧 Qt（电机/转台串口协议参考）
│   ├── RK3568开机自启动代码/        S99myspireceive 等（自启动参考）
│   └── lib/                    ⬜ 待补：aarch64 libUSB2UARTSPIIIC.so
├── spi_receiver/              【本阶段新写】SPI slave 收二进制深度帧
│   ├── README.md
│   ├── spi_receiver.c         传输层照搬 0411.c + 二进制深度帧解析
│   └── deps/                  USB2UARTSPIIICDLL.h + aarch64/x86_64 .so（待补）
├── （新）qt_display/           【本阶段新写】深度帧 → MIPI 屏实时渲染
├── motor_controller/          串口 → STM32（待实现，Python 3.8）
├── cloud_syncer/              5G 上传（已实现+离线 e2e 过）——暂缓阶段，保留不动
└── autostart/                 BusyBox init.d（待实现）
```

> 现状：`cloud_syncer/` **已完整实现并通过离线 e2e**（归暂缓阶段）；`spi_receiver/`、`motor_controller/`、`autostart/`、`qt_display/` 待实现；`legacy/` .c 与头文件已拷入，**`.so` 未拷入**（见 §7）。

---

## 3. 模块设计

### 3.1 spi_receiver —— SPI slave 收实时深度帧（本阶段核心）

**传输层（沿用旧版已验证物理链路，勿改）**

| 项 | 值 |
|----|----|
| 介质 | USB转SPI 适配器模块（USB 0483:5740，插 RK3568 USB 口） |
| 库 | `libUSB2UARTSPIIIC.so`（aarch64）+ `USB2UARTSPIIICDLL.h` |
| 时序 | SPI slave，`SPI_SubMode_0`，`SPI_MSB`（对齐哪吒 master MODE0） |
| 哪吒侧 | `/dev/spidev1.0`，MODE0，1.125MHz，需 root |

调用序列（参考 `legacy/.../spi_rev_slavemyloop0411.c` 传输层）：

```
OpenUsb(0)
ConfigSPIParamSlave(SPI_MSB, SPI_SubMode_0, 0)
loop: SPISlaveRcvData(buf, len, 0)  → 同步 MAGIC → 解析二进制深度帧 → 交 Qt 渲染
CloseUsb(0)
```

**应用层（与旧版的关键区别）**

旧版 0411.c 校验**文本帧**（`Frame=0\n` + 1024 空格整数），TOF3.0 **不复用**。本阶段为**实时二进制深度帧**：

```
[MAGIC:2B 0xABCD][CMD:1B=0x10][SEQ:4B LE][LEN:4B LE][PAYLOAD: TofFrame 2070B][CRC32:4B]
```

接收端职责：按 MAGIC 同步 → 校验 CRC32 → 解析 TofFrame → **低延迟交 Qt 渲染到 MIPI 屏 → 即弃**（RK3568 不落盘）。无文件重组、无 ACK（实时流，丢帧只影响一帧画面，不补传）。

> 文件队列协议（CMD 0x01–0x05、FILE_SEND/CHUNK/ACK）属**暂缓的 5G 批量上传阶段**，本阶段不实现。

**实现语言**：板上无 gcc → 在带 SDK 的 x86 机用 `aarch64-linux-gnu-gcc` 链接 aarch64 `libUSB2UARTSPIIIC.so` 交叉编译，产物经串口 base64 传板上。x86_64 .so 仅供开发机本地联调。

**与 Qt 显示的关系**：spi_receiver 与 Qt 显示程序可合并为一个进程（接收线程 + Qt 主线程经队列交帧），或拆两进程经共享内存/本地 socket。实现时定（开放项 O6）。

**失败不阻塞**：接收异常仅记日志重连，哪吒侧数据继续本地积累。

### 3.2 Qt 显示程序 —— MIPI 屏实时深度图（本阶段核心）

| 项 | 决策 |
|----|------|
| 平台 | RK3568 aarch64，Qt（v1.0 `SinglePhoton207_5` 已验证可在板上跑 Qt + 显示） |
| 屏 | MIPI 屏（正点原子 ATK-DLRK3568 配套） |
| 输入 | spi_receiver 解析出的 TofFrame（2KB） |
| 渲染 | 32×32 深度图伪彩（jet），与哪吒 `DepthWidget` 视觉一致；实时刷新 |
| 存储 | **不落盘**，显示完即弃 |
| 构建 | 交叉编译（qmake + aarch64 工具链 + 板上 Qt 运行库），参考 legacy Qt 工程结构 |

> 旧 `SinglePhoton207_5` 是读 `received.dat` 文本帧刷新；本程序改为消费二进制 TofFrame，渲染逻辑可参考旧 `image`/`mainwindow`。

### 3.3 motor_controller —— 镜头调焦电机

**链路**：RK3568 串口 → STM32F103 → TMC2209 → 镜头电机（滑台调焦 + 齿轮光圈）

| 项 | 值 |
|----|----|
| 串口 | 19200, 8N1；**RK3568 侧 /dev 节点待定**（ttyUSB0-4 已被 Quectel 5G 占且禁碰，STM32 应在硬件 UART /dev/ttySx，开放项 O2） |
| 帧格式 | `0xFF 0x02 [device] [cmdHi] [cmdLo] [checksum]`（6 字节） |
| checksum | `(0x02 + device + cmdHi + cmdLo) & 0xFF` |
| device | `0x01`=直线滑台(调焦) `0x02`=齿轮(光圈) |
| cmdHi | 前/顺：滑台 `0x20`、齿轮 `0x40`；后/逆：滑台 `0x22`、齿轮 `0x42` |
| cmdLo | `0x01`=粗调 `0x02`=细调 |

| 动作 | 帧 |
|------|----|
| 滑台前进 粗/细 | `FF 02 01 20 01 24` / `FF 02 01 20 02 25` |
| 滑台后退 粗/细 | `FF 02 01 22 01 26` / `FF 02 01 22 02 27` |
| 齿轮顺时针 粗/细 | `FF 02 02 40 01 45` / `FF 02 02 40 02 46` |
| 齿轮逆时针 粗/细 | `FF 02 02 42 01 47` / `FF 02 02 42 02 48` |

STM32 侧：`legacy/.../STM32F103_lensfocus_TMC2209`（uart1@19200，1/16 微步，Flash 模拟 EEPROM 存位置），Keil 编译，不在 TOF3.0 改动范围。

**控制来源（开放项 O1）**：旧版电机由 RK3568 Qt 客户端手动按钮驱动，不参与哪吒闭环。当前同此——RK3568 本地手动/独立控制。

### 3.4 cloud_syncer / net_manager —— 5G 上传【本阶段暂缓】

- `cloud_syncer`（`rk3568/cloud_syncer/`）：Python 3.8 仅标准库，扫描 buffer → POST 云端 FastAPI。**已完整实现并通过离线 e2e（3 场景 14 断言）**。本阶段不接 5G、不联调真实云，**代码保留不动**。
- `net_manager`：5G 拨号/重连/健康检测（Quectel RM500U-CNV）。**暂缓**。
- 启用条件：日后系统稳定 + 确定公网云平台地址 + RK3568 5G 联网（5G 链路本身已验证可通）。届时哪吒侧补"全量 raw+depth 批量经 SPI 文件队列 → RK3568 → 5G"上行（受带宽限制，需选择性/夜间批传，见 `ARCHITECTURE.md` §四）。

---

## 4. 数据流（本阶段端到端）

```
[哪吒] 采集 → 算法 → TofFrame(2070B)
        ├─ SpiSyncer(待写) 低延迟二进制帧 → /dev/spidev1.0 master
        └─ 本地全量存档：depth → ~/tof-data/depth_queue/（DataRecorder）
                          raw .tch(2MB) → ~/tof-data/raw_tcspc/（采集层，待 P7）
   │ USB转SPI 适配器
[RK3568] spi_receiver: MAGIC 同步 + CRC32 → 解析 TofFrame
         Qt 显示程序: 渲染到 MIPI 屏 → 即弃
         motor_controller: 串口下发电机帧 → STM32（独立）
[暂缓]   cloud_syncer + net_manager: 5G 批量上传 raw+depth → 公网云
```

带宽：深度帧 2KB，实时流 ~4KB/s（30fps 也才 60KB/s），SPI/显示均富余。原始 14GB/h 不过 SPI/5G。

---

## 5. 部署与运行（RK3568，BusyBox）

| 项 | 方案 |
|----|------|
| 系统 | Buildroot 2018.02，aarch64，Linux 4.19，root 无密码 |
| 唯一通道 | 串口 `/dev/ttyUSB0 @1500000`（无网时传文件用 base64；CH340 须慢写，见 `docs/spi硬件接口.md`） |
| 编译 | 板上无 gcc → spi_receiver / Qt 显示在 x86 SDK 机交叉编译（aarch64-linux-gnu-gcc） |
| Python | 3.8.6 板上自带 → motor_controller / cloud_syncer 直接跑 |
| 自启动 | BusyBox init.d，仿 legacy `S99myspireceive`（见 §2 autostart） |
| 部署路径 | `/myApp/tof3/{spi_receiver,qt_display,motor_controller}/`，库放 `/lib/` |
| 文件传输 | 无网时：开发机 `base64 f > f.b64` → 串口 → 板上 `base64 -d` |

---

## 6. 开放设计项（需后续决策）

| # | 问题 | 说明 |
|---|------|------|
| O1 | 电机闭环控制通道 | 哪吒无网 + SPI 本阶段只有实时深度单向流 → 哪吒 `FeedbackController` 无法实时驱动 RK3568 电机。P8/P13 需控制通道。候选：①加一条反向 SPI 控制帧；②RK3568 本地/手动。当前默认②。 |
| O2 | STM32 接 RK3568 哪个 /dev 节点 | ttyUSB0-4 是 Quectel 5G AT 口（禁碰）。STM32 应在硬件 UART（/dev/ttySx），待用户确认接线节点。 |
| O3 | RK3568 本地电机触发入口 | 无 Qt 按钮时手动控制入口（命令行 / 简单 HTTP / 物理按键）？ |
| O4 | 实时流时序细节 | 是否用适配器 INT 中断线；`SPISlavePreloadData` 用法；丢帧/重同步策略 |
| O5 | 5G 拨号（暂缓阶段） | APN、拨号脚本、断线重连；公网云平台地址 |
| O6 | spi_receiver 与 Qt 显示进程模型 | 合一进程（接收线程+Qt 队列）vs 两进程（共享内存/socket） |

---

## 7. 当前缺口

| 缺口 | 影响 | 处理 |
|------|------|------|
| `libUSB2UARTSPIIIC.so`（aarch64/x86_64）未拷入 TOF3.0 | spi_receiver 无法交叉编译/联调 | 从 `单光子项目/RK3568相关代码/RK3568使用SPI接收数据代码/` 拷入 `rk3568/spi_receiver/deps/` 与 `rk3568/legacy/lib/`（板上 `/lib/libUSB2UARTSPIIIC.so` 已存在可取） |
| 哪吒侧实时深度 SpiSyncer 未实现 | 链路上游缺失 | P-RT，`nezha/qt_app/` 新增 |
| RK3568 spi_receiver + Qt 显示未实现 | 链路下游缺失 | P-RT，交叉编译 |
| STM32 接 RK3568 串口节点未定 | motor_controller 无法落地 | 开放项 O2，待用户确认 |
| aarch64 交叉编译器未确认 | 出包依赖 | 确认 SDK 机 `aarch64-linux-gnu-gcc`（Linaro 6.3.1 匹配板子） |

---

## 8. 实施顺序建议

1. 补缺口：拷 `.so`/头文件到 `rk3568/spi_receiver/deps/`、`rk3568/legacy/lib/`
2. 定二进制深度帧协议细节（MAGIC/CMD0x10/CRC32，开放项 O4）
3. 哪吒侧 SpiSyncer：算法出帧 → 低延迟推 `/dev/spidev1.0`（需 root）
4. RK3568 spi_receiver：传输层照搬 0411.c + 二进制深度帧解析 → 交叉编译 → 板上联调
5. RK3568 Qt 显示程序：消费 TofFrame → MIPI 屏渲染（参考 legacy Qt）→ 交叉编译
6. motor_controller：Python 串口下发（待 O2 确认节点，可并行）
7. autostart 脚本（spi_receiver+Qt 显示）
8. 【暂缓】5G 阶段：net_manager + cloud_syncer 接真实云 + 哪吒批量上行
9. 验证后回写 `ARCHITECTURE.md` / `CLAUDE.md` / `progress.md`
