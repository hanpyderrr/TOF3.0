# RK3568 改版底板 — UART 映射 + 外设布局（权威参考）

> 更新：2026-05-29
> 适用板型：基于 ATK-DLRK3568 V1.5 改版，原理图 `refs/hardware/ATK-DLRK3568_改版底板原理图_2026-05-29.pdf`
> 设备树实测数据来源：板上 `cat /sys/firmware/devicetree/base/...` + `ls /dev/ttyS*`
>
> 与原版 V1.5（`refs/hardware/ATK-DLRK3568 V1.5(底板原理图).pdf`）的差异在 §四。

---

## 一、UART 实测全表

| Linux 节点 | RK3568 控制器 | 物理地址 | 设备树 status | 板上去向 | 当前进程占用 |
|---|---|---|---|---|---|
| —          | UART0 | `fdd50000` | disabled | — | — |
| —          | UART1 | `fe650000` | disabled | — | — |
| **ttyFIQ0** | UART2 | `fe660000` | disabled \* | CH340 USB-UART → 串口控制台 | Rockchip FIQ Debugger 独占 |
| **/dev/ttyS3** | UART3 (M1) | `fe670000` | **okay** | JP3 → RS422 收发器 (MAX490ESA+) | 空（RS422 未接外设） |
| **/dev/ttyS4** | UART4 (M1) | `fe680000` | **okay** | JP2 → STM32F103 USART1（板内） | 空（`motor_ctl.py` 未写，但物理已就绪） |
| —          | UART5 | `fe690000` | disabled | — | — |
| —          | UART6 | `fe6a0000` | disabled | — | — |
| —          | UART7 | `fe6b0000` | disabled | — | — |
| **/dev/ttyS8** | UART8 | `fe6c0000` | **okay** | 原理图未找到引出位置 | 空 |
| —          | UART9 (M1) | `fe6d0000` | **disabled** | JP4 pin 1/2 物理引出但内核未启用 | — |

\* UART2 在设备树里 `status="disabled"`，但物理硬件被 Rockchip FIQ Debugger 驱动直接接管，
跑 `console=ttyFIQ0`（见 `/proc/cmdline`）。两套驱动互斥，UART2 不可作应用串口用。

---

## 二、JP2 / JP3 跳线"串口功能选择"

两个 2×3 排针，决定 RK3568 UART3/UART4 与 RS422/RS485/STM32 USART1 三方向哪一边连。

### JP3「串口3功能选择」（实测短接 1-3 / 2-4）

```
列 1                  列 2
┌───────────────┬───────────────┐
│ 1 RS422_RX     │ 2 RS422_TX     │  ← MAX490ESA+ 收发器
├───────────────┼───────────────┤
│ 3 UART3_TX_M1  │ 4 UART3_RX_M1  │  ← RK3568 UART3
├───────────────┼───────────────┤
│ 5 USART1_RX_ST │ 6 USART1_TX_ST │  ← STM32 USART1
└───────────────┴───────────────┘

当前跳线：1-3 短接, 2-4 短接
  → RK3568 UART3 (ttyS3) ↔ RS422 收发器
  → STM32 USART1 在 JP3 上悬空（不走这条）
```

### JP2「串口4功能选择」（实测短接 3-5 / 4-6）

```
列 1                  列 2
┌───────────────┬───────────────┐
│ 1 RS485_RX     │ 2 RS485_TX     │  ← SP3485EN 收发器
├───────────────┼───────────────┤
│ 3 UART4_TX_M1  │ 4 UART4_RX_M1  │  ← RK3568 UART4
├───────────────┼───────────────┤
│ 5 USART1_RX_ST │ 6 USART1_TX_ST │  ← STM32 USART1
└───────────────┴───────────────┘

当前跳线：3-5 短接, 4-6 短接
  → RK3568 UART4 (ttyS4) ↔ STM32 USART1（板内）
  → RS485 在 JP2 上悬空（不走这条）
```

---

## 三、IO 扩展排针 JP4（22 针，3.3V TTL）

| Pin | 信号 | RK3568 GPIO | Pin | 信号 | RK3568 GPIO |
|---|---|---|---|---|---|
| **1** | **UART9_TX_M1** ⚠ | GPIO4_C5 | **2** | **UART9_RX_M1** ⚠ | GPIO4_C6 |
| 3 | I2C3_SDA_M0 | GPIO1_A0 | 4 | I2C3_SCL_M0 | GPIO1_A1 |
| 5 | GBC_LED | GPIO3_C5 | 6 | 5G_DISABLE | — |
| 7 | GBC_KEY | GPIO3_C4 | 8 | 5G_RESET | — |
| 9 | I2C1_SCL_TP | GPIO0_B3 | 10 | I2C1_SDA_TP | — |
| 11 | I2C4_SCL_M0 | GPIO4_B3 | 12 | WORKING_LEDEN | — |
| 13 | REFCLK_OUT | GPIO0_A0 | 14 | I2C4_SDA_M0 | — |
| 15 | SPI1_MOSI_M1 | GPIO3_C1 | 16 | SPI1_MISO_M1 | — |
| 17 | SPI1_CLK_M1 | GPIO3_C3 | 18 | SPI1_CS0_M1 | — |
| 19 | — | — | 20 | MIPICAM1_RST_L | — |
| 21 | GND | — | 22 | VCC3V3_SYS | — |

⚠ **UART9 当前在设备树里 status="disabled"**，pin 1/2 物理引出但**不能直接用**——
需要改 RK3568 内核 `.dts` 把 `&uart9 { status="okay"; pinctrl-... }` 启用，重编 dtb 烧板。

---

## 四、电机控制路径（板内全闭环）

改版板把 STM32F103C8T6 + TMC2209 ×2 **直接焊在底板**，电机控制不再外接驱动板。

```
RK3568 UART4 (/dev/ttyS4) ────┐
                              │ JP2 短接 3-5 / 4-6
                              ▼
                  STM32F103 USART1 (PA9/PA10)
                              │
                              ▼
                  STM32 GPIO 控制信号
                  PA0 (DIR1), PA1 (EN1), PA2 (MS1_1), PA3 (MS2_1), PA7 (STEP1)
                  PB8 (DIR2), PB9 (EN2), ...
                              │
            ┌─────────────────┴─────────────────┐
            ▼                                   ▼
        TMC2209 #1                          TMC2209 #2
            │                                   │
            ▼                                   ▼
       MOTOR1 接线柱（A1/B1）             MOTOR2 接线柱（A2/B2）
            │                                   │
       镜头调焦滑台                          光圈齿轮
```

**STM32 烧录**：P13 排针 SWD（SWCLK_ST / SWDIO_ST / VCC3V3_SYS / GND）→ STLink V2
**STM32 启动**：BOOT0_ST 跳线选 Flash 启动
**STM32 复位**：NRST_ST 复位按键

**软件层现状**：`rk3568/motor_controller/motor_ctl.py` 尚未实现。
STM32 固件来源：`rk3568/legacy/.../STM32F103_lensfocus_TMC2209`，Keil 编译，19200 8N1。

---

## 五、与原版 V1.5 的差异

| 模块 | V1.5 原版 | 改版 | 备注 |
|---|---|---|---|
| **STM32** | 外挂模块 | ✅ **板上焊死** | TMC2209 同步上板 |
| **TMC2209** | 外挂驱动板 | ✅ **板上 ×2** | MOTOR1 / MOTOR2 |
| **RS422** | ❌ 无 | ✅ **新增**（MAX490ESA+ + JP3 跳线选择） | 当前未接外设 |
| RS485 | ✅ 有 | ✅ 保留 + JP2 跳线选择 | 当前跳到 STM32 侧不用 RS485 |
| RS232 (DB9) | ✅ 有 | ❌ 删 | 改版去掉 SP3232 与 COM1 |
| 6 轴传感器 SH3001 | ✅ 有 | ❌ 删 | |
| TF Card | ✅ 有 | ❌ 删 | |
| HW_ID 电阻分压 | ✅ 有 | ❌ 删 | |
| KEY 矩阵 4 键 | ✅ 有 | ❌ 删（只剩 SARADC 1 键 KEY） | |
| IR Receiver | ✅ 有 | ❌ 删 | |
| CAN | ✅ 有 | ❌ 删 | |
| AUDIO | ✅ 有 | ❌ 删 | |
| HDMI | ✅ 有 | ❌ 删 | |
| 5G 模块 (RM500U) | ✅ 有 | ✅ 保留 | |
| MIPI DSI | ✅ 有 | ✅ 保留 | |
| USB 2.0/3.0/OTG | ✅ 有 | ✅ 保留 | |
| RTC AT8563T | ✅ 有 | ✅ 保留 | |

---

## 六、当前外接 / 待接外设

| 状态 | 外设 | 接口 |
|---|---|---|
| ✅ 已接 | 哪吒 USB-SPI 适配器 (0483:5740) | USB 2.0 Host |
| ✅ 已接 | MIPI DSI 显示屏 | J4 |
| ✅ 已接 | CH340 USB-UART (调试) | USB → ttyFIQ0 |
| ✅ 已接 | 5G SIM 卡 | Nano SIM |
| ⏸ 物理就绪未启用 | 镜头电机 ×2（滑台 + 光圈齿轮） | MOTOR1 / MOTOR2 接线柱（板内 STM32 已焊好） |
| ⏳ 待接 | 激光器 YSC-SO-M04-4 | 推荐拔 JP3 跳线 → 接 pin 3/4 → ttyS3（见 §七） |
| ❌ 未接 | RS422 收发器 | A/B/Y/Z 接线柱 |

---

## 七、激光接线方案（推荐）

激光器 YSC-SO-M04-4 是 **Modbus RTU 9600 8N1**，串口四线：电源 V+/V- + TX/RX。

### 推荐：拔 JP3 跳线 → 接 ttyS3

| 操作 | 详情 |
|---|---|
| 1. 物理拔 JP3 跳线帽 | 拔掉 JP3 上的 1-3 和 2-4 两个跳线帽（让 UART3 与 RS422 断开）。拔之前可拍照记录原状以便恢复。 |
| 2. 引激光线 | JP3 pin 3 (UART3_TX_M1, 3.3V TTL) → 激光 RX；JP3 pin 4 (UART3_RX_M1, 3.3V TTL) → 激光 TX |
| 3. 接 GND | 板上任意 GND → 激光 GND（**必须共地**） |
| 4. 激光电源 | 独立 12V/24V 直流供电（按激光手册），**不接板子电源** |
| 5. 软件 | Linux 节点 `/dev/ttyS3`，波特率 9600 8N1，Modbus RTU 主站 |

### ⚠ 电平兼容性

板子 UART3_M1 是 **3.3V TTL**。激光器 P3 串口 TTL 可能是 3.3V 或 5V，必须确认：
- 3.3V TTL → 直连
- 5V TTL → 加 TXS0108E 类双向电平转换板（淘宝几块钱）

### 为什么不接 JP4（UART9）

JP4 pin 1/2 是 UART9_TX_M1/RX_M1，但 **UART9 设备树 disabled**，Linux 没有 `/dev/ttyS9`，
要启用需要改内核 `.dts` 重编 dtb 烧板，成本远大于拔 JP3 跳线。

### 替代方案（紧急情况）

| 方案 | 操作 | 何时用 |
|---|---|---|
| B. 拔 JP2 跳线，给激光 ttyS4 | 拔 JP2 上 3-5/4-6，从 pin 3/4 引线 | 此时电机失去 UART4 通道，整个电机控制断了 — **不推荐** |
| C. 启用 UART9 → JP4 接激光 | 改 RK3568 `.dts` 重烧 dtb，激光接 JP4 pin 1/2 | 想保留 RS422 + 电机都不动时 |

---

## 八、UART2 跑 FIQ Debugger 的说明

为什么 UART2 设备树 `status="disabled"` 但串口控制台还能用？

```
设备树标准驱动（8250-uart）路径：
  serial@fe660000 status="okay" → /dev/ttyS2（应用层可用）

FIQ Debugger 路径（Rockchip 专用）：
  serial@fe660000 status="disabled" → 标准驱动不接管
       ↓
  fiq_debugger 模块直接占用硬件寄存器
       ↓
  /dev/ttyFIQ0，console=ttyFIQ0（仅做控制台，不暴露给应用）
```

两套互斥，改版板选了方式 B。代价：
- ✅ FIQ 优先级超过 IRQ，内核 panic / 用户态死循环时控制台仍可输出
- ❌ UART2 不能给应用层做普通串口用

`/proc/cmdline` 关键参数：

```
earlycon=uart8250,mmio32,0xfe660000   # 引导期 8250 寄存器直接打 printk
console=ttyFIQ0                        # 运行期 FIQ Debugger 接管同一硬件
```

---

## 九、相关文档与开放项收口

| 文档 | 关系 |
|---|---|
| `refs/hardware/ATK-DLRK3568_改版底板原理图_2026-05-29.pdf` | 改版板权威原理图 |
| `refs/hardware/ATK-DLRK3568 V1.5(底板原理图).pdf` | 原版参考 |
| `refs/hardware/AAEON_哪吒_用户手册_含pinout.pdf` | 哪吒 SBC 完整 pinout（HAT GPIO + CN1~CN11） |
| `refs/hardware/哪吒.pdf` | 哪吒 SBC 规格简表 |
| `refs/hardware/YSC-SO-M04-4 脉冲激光驱动器（综合型）说明书.pdf` | 激光器手册（5V TTL Modbus RTU 9600） |
| `docs/rk3568_framework.md` | RK3568 软件栈框架（与本文档互补，软件层为主） |
| `docs/登录方式.md` | 串口/SSH 登录细节（不受改版影响） |
| `rk3568/motor_controller/README.md` | 电机控制模块设计（节点已确认为 ttyS4） |

## 十、哪吒侧 UART 速查（补充，激光接哪吒不接 3568）

虽然本文档以 RK3568 为主，但因为激光留在哪吒，把哪吒 UART 接法也放这里方便对照。

```
哪吒 AAEON「哪吒」SBC，连接器 CN1~CN11，详见
  refs/hardware/AAEON_哪吒_用户手册_含pinout.pdf

可用 UART：
  ① CN3 40-pin HAT GPIO（树莓派兼容）
       pin 8  = UART_TX / GPIO16   ← 给激光 RX
       pin 9  = GND                 ← 共地
       pin 10 = UART_RX / GPIO17   ← 接激光 TX
       pin 11 = RTS / GPIO4         ← 可选流控
       pin 36 = CTS / GPIO26        ← 可选流控
       电平：3.3V TTL
       Linux 节点：待 SSH 哪吒确认（应为 /dev/ttyS?）

  ② CN7 10-pin USB2.0/UART wafer
       具体 pinout 哪吒用户手册未给，需进一步查 AAEON 详细文档
       理论上也是 3.3V TTL

激光器 YSC-SO-M04-4 控制串口（5V TTL，4 线）：
  5V   ← 独立 5V 适配器（不取 HAT 5V，避免抖动）
  GND  ↔ 哪吒 CN3 pin 9
  RX   ← 哪吒 CN3 pin 8 (UART_TX) 经电平转换 (3.3V→5V)
  TX   → 哪吒 CN3 pin 10 (UART_RX) 经电平转换 (5V→3.3V)

中间必需：5V↔3.3V 双向电平转换板（TXS0108E 类）
  原因：哪吒 GPIO 输入耐压 ≤3.6V，直接吃激光 5V TX 会烧
```

**收口的开放项**：
- O2「STM32 接 RK3568 哪个 /dev 节点」→ **已确定 = `/dev/ttyS4`**（JP2 短接 3-5/4-6）

**仍开放**：
- O1「电机闭环控制通道」（仍未规划）
- UART8 (ttyS8) 引出位置在原理图未找到，软件层启用但物理上未确认能用
