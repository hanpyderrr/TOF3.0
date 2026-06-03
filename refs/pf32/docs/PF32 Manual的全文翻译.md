# PF32 Manual的全文翻译.pdf

> PF32 SPAD 探测器完整用户手册中文翻译（v1.5.14，Photon Force）

## 关键信息

### TRIG 输出信号（本项目核心）

| 参数 | 值 |
|------|-----|
| 连接器 | SMA，标注 **TRIG**（Output 侧） |
| 电压范围 | **0 to 3.3V** |
| 最大频率 | **100MHz** |
| 信号描述 | "External laser source trigger signal (output)" |

**sys_master 模式下**：PF32 内部 FPGA 产生同步脉冲，经 **TRIG SMA** 输出（3.3V）触发激光。激光收到后发光，SPAD 检测反射光子，TDC 以光子到达时刻为 start，下一个 TRIG 脉冲为 stop（反向启停）。

### SMA 接口全表（顶部面板）

| Name | Voltage Range (V) | 方向 | 描述 |
|------|-------------------|------|------|
| FRM | 0–5 | Input | Frame sync（扫描系统用） |
| LINE | 0–5 | Input | Line sync |
| PIXEL | 0–5 | Input | Pixel sync |
| BLK | 0–5 | Input | Blanking input |
| SYNC | 0–3.3 | Input | External laser sync input（laser-is-master 时用） |
| **TRIG** | **0–3.3** | **Output** | **激光触发信号输出（sys_master 时用）** |
| SHUT | 0–3.3 | Output | Shutter output |

### 两种 TCSPC 工作模式

| 模式 | 时钟主体 | SYNC 用法 | TRIG 用法 |
|------|----------|-----------|-----------|
| laser-is-master | 激光驱动器 | 激光 SYNC Out → PF32 SYNC In | 不用 |
| **sys_master（本项目）** | **PF32 内部** | 不用 | **PF32 TRIG Out → 激光 Ext Trig In** |

### 技术规格摘录

| 参数 | 值 |
|------|-----|
| 阵列 | 32×32 SPAD |
| 时间分辨率 | 55ps/bin，1023 bins（10-bit TDC） |
| 时间范围 | 55ps–57ns（最大无歧义距离 ~8.5m） |
| IRF（抖动） | ~150ps（SPAD 阵列内） |
| Laser sync 输入/输出幅度 | 3.3V |
| 最大激光同步频率 | 100MHz |
| 光子探测效率峰值 | 28% @ 500nm |

### 反向启停原理

PF32 执行反向启停：光子到达触发 TDC 计时（start），下一个 TRIG 同步脉冲停止计时（stop）。距离公式：

```
distance = (1023 - bin) × 55ps × c / 2
```

bin 越小 = 飞行时间越长 = 目标越远。
