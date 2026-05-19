# RK3568 回归架构思考：5G 上行通道

> ⚠️ **本文为早期思考记录，多处已被推翻，仅留档。权威设计见 [`rk3568_framework.md`](rk3568_framework.md)、[`../ARCHITECTURE.md`](../ARCHITECTURE.md)。**
> 已锁定决策（2026-05-19）推翻本文：
> - "电机经 SPI CMD=0x06" / "MotorUart 保留哪吒" → **RK3568 直连 STM32 串口本地控制**
> - "哪吒 spidev0.0 ↔ RK3568 原生 SPI slave" → **USB转SPI 适配器做 slave**（物理链路已实测通）
> - "SPI 纯文件队列异步、不做实时流" / "RK3568 不做显示" → **深度帧走 SPI 实时流；RK3568 实时 Qt MIPI 屏显深度图**（那是为 2MB 原始定的，2KB 深度帧带宽富余）
> - "哪吒无网→必经 SPI→5G 上云" → **5G 上云本阶段暂缓**；原始 TCSPC 只哪吒本地存档
>
> 版本：2026-05-18
> 背景：哪吒无网络，RK3568 有 5G 模块 + 已有电机控制代码，重新考虑双机协作

---

## 一、问题起点

| 设备 | 当前状态 | 关键能力 |
|------|---------|---------|
| 哪吒 NUC (N97) | 主机，无网络 | PF32 采集、算法处理、本地存储、Qt UI |
| RK3568 | 搁置 | 5G 上网、电机控制（v1.0 已实现）、HDMI |

**当前架构的问题**：CloudSyncer 在哪吒侧持续 queue，但哪吒无网，数据永远上不去。

**重新引入 RK3568 的核心价值**：提供 5G 上行通道，不是替代哪吒的算法能力。

---

## 二、新双机架构

```
PF32 探测器 (USB/Opal Kelly)
    |
哪吒 NUC (Intel N97) ── HDMI → 显示器
    |
    ├── ExampleTOF/sim_pf32       采集 TCSPC 原始数据
    ├── 算法模块                   TCSPC → 深度图 + 置信度图
    ├── FeedbackController
    │   ├── LaserUart              /dev/ttyUSB0 (Modbus RTU)
    │   └── MotorUart              /dev/ttyUSB1 (STM32) [保留在哪吒侧]
    ├── 本地存储 ~/tof-data/
    │   ├── depth_queue/           轻量帧 (2KB/帧)
    │   └── raw_tcspc/             原始直方图 (2MB/帧)
    └── SpiSyncer（新）            定期通过 SPI 推送待上传数据
         |
         | SPI (哪吒=master, RK3568=slave)
         |
RK3568 ── 5G 模块
    |
    ├── SpiReceiver（新）          接收哪吒推来的数据，写本地缓冲
    ├── CloudSyncer（新/移植）     HTTP 上传到云端 FastAPI
    ├── 本地缓冲 ~/tof-buffer/    暂存待上传文件
    └── 电机控制（可选复用v1.0）   若后续 STM32 改接到 RK3568

云端 FastAPI (不变)
    ├── POST /api/frames/depth
    ├── POST /api/frames/tcspc
    └── GET  /api/sessions
```

---

## 三、为什么这次 SPI 不会像之前那样脆弱

之前 SPI 出问题的原因：**实时流传输**，哪吒采集的原始数据要实时推给 RK3568 再处理，一帧 2MB、2fps，4MB/s 已经超出 SPI 稳定带宽，且需要严格同步。

新方案的不同：

| 维度 | 之前 | 现在 |
|------|------|------|
| 传输模式 | 实时流 | 文件队列，异步 |
| 传输内容 | 原始 TCSPC → RK3568 处理 | 哪吒已处理好的结果 / 已存好的文件 |
| 带宽要求 | 4MB/s 连续 | 轻量帧 < 10KB/s，可断续 |
| 同步要求 | 严格帧同步 | 不需要，ack 确认即可 |
| 故障影响 | SPI 断 → 整个系统停 | SPI 断 → 数据继续本地存，等恢复再补传 |

---

## 四、SPI 协议设计

### 4.1 物理层

```
硬件：
  哪吒：40pin GPIO 扩展接口，使用 spidev0.0（Linux spidev 驱动）
  RK3568：SPI 外设（slave 模式）
  连接：MOSI / MISO / SCLK / CS（4线 SPI）+ INT 中断线

SPI 时钟：1~4 MHz（保守，稳定性优先）
哪吒：master (spidev0.0)
RK3568：slave (spi 外设)
额外信号：
  INT（RK3568→哪吒 GPIO）：RK3568 有网且 buffer 有空间时拉高，通知哪吒可以发送
  CS（哪吒→RK3568）：片选
```

### 4.2 应用层协议

```
帧格式：[MAGIC:2B 0xABCD] [CMD:1B] [SEQ:4B] [LEN:4B] [PAYLOAD:N] [CRC32:4B]

CMD 定义：
  0x01 QUERY_STATUS    哪吒查询 → RK3568 回复：{网络状态, buffer剩余, 上传队列长度}
  0x02 FILE_SEND       哪吒发送文件头：{filename, total_size, chunk_count}
  0x03 FILE_CHUNK      哪吒发送文件块：{chunk_index, data[N]}
  0x04 FILE_ACK        RK3568 确认收到完整文件：{filename, status}
  0x05 UPLOAD_STATUS   RK3568 主动上报：{上传进度, 最后成功seq, 错误信息}
```

### 4.3 传输时机

```
哪吒侧 SpiSyncer（后台线程，低优先级）：
  每 5 秒：发送 QUERY_STATUS
  若 RK3568 有网且 buffer < 80%：
    优先推送 depth_queue/ 最旧的未上传帧（2KB，快速）
    空闲时推送 raw_tcspc/ 分块传输（每块 64KB，SPI 带宽内）
  若 SPI 传输失败：记录日志，下次重试，不影响采集主线程
```

---

## 五、电机控制归属（已确认）

**RK3568 上预留了电机驱动引脚，直接插上使用。**

```
哪吒 → SPI → RK3568 → 电机驱动引脚 → TMC2209 → 镜头电机
            [CMD=0x06 MOTOR_CMD]
```

**理由**：
- RK3568 v1.0 已有完整电机驱动代码，直接复用
- RK3568 有专用电机引脚，接线更干净
- 哪吒 USB 口释放 `/dev/ttyUSB1`，只留 PF32 + LaserUart 两个

**延迟影响**：
- 哪吒发 SPI 电机命令 → RK3568 执行：约 5~10ms 额外延迟
- 焦距调节非实时控制（P8 闭环是秒级），10ms 延迟可接受

**代码适配**：
- 哪吒 `MotorUart` 改为 `MotorController` 抽象基类
- 实现 `SpiMotorController`（通过 SPI 发 CMD=0x06）替换原有串口实现
- FeedbackController 依赖接口，无需修改逻辑

---

## 六、数据流时序

```
T=0ms      ExampleTOF 采集一帧 TCSPC [2MB]
T=10ms     算法处理 → depth_map (2KB) + confidence_map
T=15ms     写本地：depth_queue/ + raw_tcspc/
T=50ms     FeedbackController 评估激光/电机
           ↑ 主线程，不受网络/SPI 影响

[后台线程，5s 周期]
T=5s       SpiSyncer 查询 RK3568 状态
T=5.1s     若有网且 buffer 空余 → 推送 depth_queue/ 最旧帧 (~2KB, <50ms)
           若空闲时间足够 → 推送 raw_tcspc/ 一块 (64KB, ~500ms@1MHz SPI)

[RK3568 侧，持续]
           SpiReceiver 写入本地 buffer
           CloudSyncer POST → 云端
           上传成功 → 删本地 buffer，通知哪吒（下次 QUERY 时回报）
```

---

## 七、现有代码的改动量评估

| 模块 | 改动 | 改动量 |
|------|------|--------|
| `qt_app/cloudsyncer.cpp` | 改为当哪吒有网时直接上传，无网时转为 SPI 推送 | 中 |
| `qt_app/mainwindow.cpp` | 上传状态 UI：区分 SPI 推送状态 vs HTTP 上传状态 | 小 |
| `acquisition/` | 不变 | 无 |
| 新增 `spi_syncer/` (哪吒侧) | SPI master：查询、推送、ack 处理 | 中 |
| 新增 `rk3568/` (RK3568 侧) | SPI slave + CloudSyncer + 5G 管理 | 大 |
| `cloud/server/` | 不变（FastAPI 接口不变） | 无 |

---

## 八、与 ML 路径的关系

RK3568 回归后，ML 训练数据的上传路径：

```
哪吒 raw_tcspc/ (2MB/帧)
    ↓ SPI (批量，空闲期，~1MB/s)
RK3568 本地缓冲
    ↓ 5G (上行带宽允许时)
云端 /api/frames/tcspc
    ↓
ML 训练数据集
```

估算：若 5G 上行 5Mbps，每帧 2MB = 3.2s 上传；  
2fps 采集 → 每小时约 14GB，5G 上传延迟约 7 倍实时，适合夜间批传。  
→ `raw_tcspc` 仍以本地优先，5G 上传作为离线补传。

---

## 九、阶段规划

| 阶段 | 任务 | 前提 |
|------|------|------|
| 当前 | 架构设计确认，SPI 协议定稿 | 本文档 |
| P7 联调后 | 在哪吒侧实现 SpiSyncer（master），先只查询 RK3568 状态 | 真实 PF32 |
| RK3568 接入后 | 实现 SpiReceiver + 移植 CloudSyncer | RK3568 复活 |
| 验证通过后 | 更新 ARCHITECTURE.md，更新 AGENTS.md | - |

---

## 十、遗留问题（已确认/未确认）

| 问题 | 状态 | 说明 |
|------|------|------|
| 哪吒 SPI 硬件接口 | ✅ 确认 | 有 40pin GPIO 扩展，使用 spidev 驱动 |
| 电机控制归属 | ✅ 确认 | RK3568 有电机驱动引脚，直接插上使用 |
| RK3568 SPI slave 实现 | ⬜ 待确认 | v1.0 代码是否有 SPI 驱动基础？ |
| 5G 模块管理 | ⬜ 待实现 | AT 命令控制，网络检测守护进程 |
| 激光器保留在哪吒 | ✅ 确认 | FeedbackController 实时反馈，不过 SPI |
| STM32 接线迁移 | ⬜ 硬件操作 | 从哪吒 /dev/ttyUSB1 改接 RK3568 电机引脚 |
