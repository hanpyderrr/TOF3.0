# 工作进度

> 最后更新：2026-05-28
> 主控：Claude Opus 4.7

---

## 当前状态快照

**架构锁定并全项目文档重写：RK3568 实时 Qt MIPI 显示深度图；深度走 SPI 实时流；原始只哪吒本地存；5G 上云暂缓。SPI 物理链路已实测逐字节通。**

| 节点 | 状态 |
|------|------|
| 哪吒侧代码（P1–P6, P5a/b/c） | ✅ 已迁移；P5b/c（哪吒 CloudSyncer/FastAPI）仅本地开发用 |
| 哪吒 SSH 连通 | ✅ 192.168.31.127 ding/1234（paramiko；调试期有网） |
| RK3568 串口连通 | ✅ `/dev/ttyUSB0`@1500000（CH340 须慢写，见 docs/spi硬件接口.md） |
| **SPI 物理链路 哪吒→适配器→RK3568** | ✅ **实测逐字节通**（旧文本协议验证，详见 docs/spi硬件接口.md） |
| RK3568 5G | ✅ 插 SIM 冷启动后已注册联网（暂缓接入，本阶段不用） |
| 架构锁定 + 文档重写 | ✅ ARCHITECTURE/CLAUDE/framework/README/progress 已按锁定决策重写 |
| cloud_syncer 深度上传 | ✅ 已实现+离线 e2e；**归暂缓阶段，保留不动** |
| P-RT 实施计划 | ✅ `docs/realtime_display_plan.md`（裸帧/文件桥/7步，已批准）|
| 交叉编译环境 | ✅ `~/rk3568_linux_sdk` Buildroot：gcc 10.3.0 + qmake Qt5.15.2 sysroot，与板同源 |
| 哪吒 spi_syncer（实时深度发送端） | ✅ `nezha/spi_syncer/` 已实现，x86_64 编译通过（移植 spisendTOF + seq 去重）|
| RK3568 spi_receiver | ✅ `rk3568/spi_receiver/` 已实现，aarch64 交叉 + x86_64 编译通过；deps .so 已入库 |
| RK3568 Qt MIPI 显示程序 | ✅ `rk3568/qt_display/` 已实现，SDK qmake 交叉编译通过（Qt5.15.2）|
| RK3568 自启脚本 | ✅ `rk3568/autostart/S95tof_spi_receiver`+`S96tof_display`（文件桥 /tmp/received.dat）|
| 板上联调（数据链路） | ✅ **端到端实测通过**：哪吒 sim→spi_syncer→SPI→适配器→spi_receiver→received.dat(2070B,seq 递增 ~2fps,crc 全过) |
| 板上联调（数据链路·二轮） | ✅ **USB reset 后再次端到端实测通过**：seq 实时持续递增（564→590→830） |
| 板上联调（屏显/稳定性） | ✅ **已交叉编译部署，屏显实时深度图正常**；旧 v1.0 自启已禁用（开机三阶段消除）|
| 哪吒开机自启（systemd） | ✅ `nezha/autostart/` tof-acquisition + tof-spi-syncer，重启验证；旧 v1.0 crontab 已禁 |
| RK3568 开机自启 | ✅ S95/S96 已装并验证；旧 `S51mydisplay`/`S99myspireceive` 改名 `DISABLED.*` 真正禁用 |
| ToF 雾分离算法早期原型 | ✅ `research/tof_sim.py` + `research/tof_process.py` 仿真验证（中雾 4m：argmax 16%→分离 96%）；**PF32 reverse 路线，与当前 research/algorithms/ 主线分歧** |
| 算法研究 Phase A（Gutierrez 64×64 forward 路线） | ✅ `research/` 主线：5 算法实测，argmax_spad 0.579≈ds_argmax 0.580；spatial_3x3 47.8% > lmf 37.5%（低 SBR 低光子） |

---

## RK3568 硬件摸底（2026-05-18）

### 基本信息

| 项目 | 详情 |
|------|------|
| 板型 | ATK-DLRK3568（正点原子） |
| 系统 | Buildroot 2018.02-rc3（2024-08-29 编译） |
| 架构 | aarch64 |
| 登录 | root，无密码，开机自动进 shell |
| 内核 | Linux 4.19.232 aarch64，#4 SMP 2025-01-13（Linaro GCC 6.3.1） |
| 串口 | Linux `/dev/ttyUSB0`（CH340 `1a86:7523`），1500000 8N1；Windows COM7 为历史记录 |

### 可用环境

| 工具 | 版本 | 说明 |
|------|------|------|
| Python | 3.8.6 | ✅ 可直接写脚本 |
| Perl | 已装 | |
| BusyBox | v1.34.1 | 基本工具齐全 |
| make | 4.2.1 | ✅ |
| pip3 | 已装 | ✅ 可装 pyserial 等（开发主机端未装 pyserial，用 termios） |
| gcc/g++ | **无** | ❌ 不能原生编译 C/C++ |
| cmake | 无 | |

### 网络现状（2026-05-19 更新）

| 接口 | 状态 | 备注 |
|------|------|------|
| 哪吒 enp1s0 | UP，192.168.31.127，可上公网 | **生产无网，当前网线仅调试**；生产态数据不经哪吒上云 |
| RK3568 usb0 (5G) | ✅ 插 SIM 冷启动后已注册联网（NAT 出口） | China Telecom；**本阶段暂缓接入** |
| RK3568 eth0/eth1 | DOWN | 未接网线 |

> 5G 初次失败根因：SIM 未在模块上电时在位 → 冷启动（带 SIM）后注册成功。5G 链路本身已验证可通，但本阶段不接入（5G 上云暂缓）。

### SPI 设备树（2026-05-18 串口实测）

| 控制器 | status | 说明 |
|--------|--------|------|
| `spi@fe610000` | **disabled** | 未启用（此前文档假设的总线，实际不可用） |
| `spi@fe620000` | **okay** | 唯一启用；设备树已挂子节点 `stm32spi@0`（STM32 调焦电机） |
| `spi@fe630000` | disabled | 未启用 |
| `spi@fe640000` | disabled | 未启用 |

- spidev 驱动已加载，**`/dev/spidev1.0` 存在**。
- ✅ **已决策（2026-05-19）**：RK3568 侧不使用原生 SPI，改用 **USB转SPI 适配器模块**做 slave（沿用旧版已验证链路），fe620000 被 STM32 占用的问题就此绕开。详见 `docs/rk3568_framework.md`。

---

## 已完成工作记录

### 2026-05-26 (深夜) — 架构 Q1–Q5 + 阶段 1 计划定稿

**Q1–Q5 决策**（仍有效）：
- Q1 接口：传统函数式 `estimate(sample, cfg) → DepthEstimate`；ML 类式 `Estimator` ABC
- Q2 `tof_process.py` v1：留原地不动；阶段 2 加 adapter 包一层
- Q3 ML 路线：算法态 PyTorch 在算法目录，收敛后搬 `ml_offline/`
- Q4 `runs/` 目录全 `.gitignore`；Q5 配置阶段 1 dataclass，阶段 2 再 YAML

**方向调整**：先做峰值检测到目标，再加雾——理由是先打通 loader/bin/换算。

> ⚠️ **路径已迁移**：原计划放 `nezha/algorithm/`，后于 05-27/28 整体迁到 `research/`。
> 引文里出现的 `nezha/algorithm/...` 路径请按 `research/...` 理解。

---

### 2026-05-26 (晚) — 算法研究态启动：Gutierrez 数据 + loader/inject_fog 第一版

**方向**：先研究算法（公开数据 64×64 forward），后降级 PF32；ml_offline 工程化推迟到算法收敛后。

**做了**：
- 新增 `docs/algorithm_test_plan.md`、`docs/algorithm_code_architecture.md`
- 拉取 Gutierrez SimSPADDataset_min 到本地（PSF 47K + scene_group0.zip 6.1G，未解压，走 Clash 7890）
- 写 `sim_spad_loader.py`（SpadSample 契约，64×64 forward 默认）与 `inject_fog.py`（Gamma 模型三档雾）
- `inject_fog.py` smoke test 通过

> ⚠️ **路径已迁移**：代码原放 `nezha/algorithm/`，后整体迁到 `research/`。
> `docs/algorithm_code_architecture.md` 里 `nezha/algorithm/` 路径已陈旧，
> 实际代码在 `research/`，参见 `docs/research_code_style.md`。

### 2026-05-26 — 离线训练 + 边缘推理架构落地:ml_offline/ 骨架 + schema + policy

**背景:** 用户调整 ML 方向——**不上云**,改为"本地实时显示 + 离线下载哪吒数据训练 + ONNX 边缘部署(默认哪吒 N97,3568 NPU 备用)"。原 `cloud/ml/` 命名误导,需要重命名 + 扩展结构。

**已确认决策(2026-05-26):**
1. **训练机器**:TBD(用户另找,候选:自建 GPU 工作站 / 临时租云 / 本机 CPU 退化)
2. **场景元数据**:**自动推断为主**——manifest/frame_record 字段大部分由进程读硬件/系统填,操作员只在会话启动时给 4 个 CLI 参数(`--location --scene --fog --pair-with`)
3. **新模型上线**:**影子模式**——v_next 与 v_current 并行跑 N 天对比指标,通过才切主路,异常自动回滚
4. **raw 保留触发阈值**:**起步值,后期标定**——落进 `policy/event_trigger.yaml`(Q ±3σ over 100-frame rolling + 每 600 帧定时采样)

**做了(纯文档/骨架,零代码风险):**
- `git mv cloud/ml ml_offline`(14 文件,保留历史)
- 新增 `ml_offline/schema/`:`session_manifest.schema.json` + `frame_record.schema.json` + README
  - `additionalProperties: false` 防止字段拼写错混进数据
  - 通过 JSON Schema Draft 2020-12 meta-schema 校验,样例 manifest+frame 实例验证通过
- 新增 `ml_offline/data/{raw_dump,meta,labels}/`:子目录骨架 + README,数据驱动布局
  - `data/meta/<session_id>/` 放轻量元数据(MB 级,全量 rsync)
  - `data/raw_dump/<session_id>/` 放 raw .tch + depth .tofrec(GB 级,选择性 rsync)
  - `data/labels/` 自动生成的弱监督标签(long_exposure_64x / level0_physical / clear_pair / calib_target)
- 新增 `ml_offline/eval/README.md`:A/B + 影子模式 + 模型语义版本号约定
- 新增 `ml_offline/policy/`:`event_trigger.yaml` + `shadow_mode.yaml` + README
  - 起步值标注 `# starter, tune after ...`,改动留旧值在注释里
- 重写 `ml_offline/README.md`:含数据/模型生命周期图 + 标签策略 + 字段填充方式
- 同步 `CLAUDE.md`/`ARCHITECTURE.md` 目录结构(cloud/ml → ml_offline)
- `.gitignore` 排除 `*.tch`/`*.tofrec`/`ml_offline/data/*/` 子目录

**验证:** schema 用 `jsonschema` 库做了 meta-schema 校验 + 样例实例验证,均通过。其他都是文档/目录骨架,无代码风险。

**遗留(Phase A 末尾再做,本次范围外):**
1. `nezha/acquisition/start_session.sh` — 会话启动脚本(组装 manifest + 启 acquisition)
2. `ml_offline/tools/validate_session.py` — 离线验证 session 目录合规
3. `ml_offline/data/tof_dataset.py` 增强以按 manifest 索引数据集
4. `tof_sim.py` 升级(pile-up / Gamma / Skewed peak / Middlebury loader)
5. `nezha/ml_runtime/` ONNX Runtime 推理封装(线上推理路径)
6. `deploy/sync_raw.py` 哪吒→开发机 rsync 同步脚本

### 2026-05-25 — 激光 PF32 同步机制确认 + 激光驱动外触发完善

**背景：** 准备完善激光驱动（PF32 未到，代码先行）。核心问题：激光怎么与 PF32 TTL 同步。

**查证结论（手册 + 旧采集代码，权威）：**
- PF32 两种 TCSPC 模式（`refs/pf32/.../PF_API.py:32-33`）：`LASER_MASTER`(1) 收激光 SYNC 做 TDC stop；`SYS_MASTER`(2) PF32 出 TRIG + 内部 EXTSTOP 做 stop。
- **实际采集代码 `单光子项目/TOF/哪吒端/ExampleTOF.cpp`、`C++/FW_Histogramming.cpp` 全部用 `TCSPC_sys_master`** → 确定 **PF32 做主、PF32 TRIG 输出触发激光**，激光必须工作在外触发模式。与反向 start-stop 公式 `(1023-bin)×55ps×c/2` 自洽。
- ⚠️ `refs/pf32/docs/SyncInput_3300mV.pdf`（3.3V SYNC 输入上限）讲的是**反向接法**（激光 SYNC→PF32 SYNC 输入，即 laser_master），**不适用本项目**，勿据此去接 PF32 SYNC 口。
- 激光器 YSC-SO-M04-4（手册）：Modbus RTU 9600 8N1；P3=TTL（外触发输入 / 同步输出 二选一）；重复频率 1Hz–1MHz（默认5k）、脉宽 5–200ns（默认10）、电压 1–200级（默认50）。
- **关键：外触发模式下激光重复频率由 PF32 TRIG 决定，激光自身 `setFreqHz` 无意义。**
- 待实物确认：**PF32 TRIG 输出电平 vs 激光 TTL 输入门限**（手册只写"TTL"未给门限，可能需电平转换；风险方向是"驱不动"，非"烧设备"）。

**代码核对（`nezha/qt_app/laseruart.cpp`）：**
- Modbus 帧格式 / 功能码（01电压 02频率 03脉宽 04脉冲模式 06读取）/ 4B 大端数据 / CRC16 与手册逐条一致 ✓
- `readParams` 解析与手册返回实例 `06 06 15 00 00 13 88 00 06 00 00 00 E5 41`（14B）对不上，且手册表格(13B)与实例(14B)自相矛盾 → 标注存疑，待实物 sscom 抓包再修正。

**改动：**
- `laseruart.h`：加同步架构文件头注释；新增 `m_extTrigger` 状态；修正 `LaserParams.mode` 注释（0=off / 1=internal / 2=external）。
- `laseruart.cpp`：`setExternalTrigger/setInternalTrigger` 维护 `m_extTrigger`；`setFreqHz` 在外触发模式下拒绝并 `emit errorOccurred`；`readParams` 加存疑警告注释。
- 调用方 `mainwindow.cpp:32` 仅用 `setExternalTrigger`，未受影响。

**验证：** 开发机无 Qt5，未本地编译；改动为状态逻辑 + 注释，无 API/头文件变化，风险低，需哪吒 `qmake && make` 验证。

**遗留：**
1. PF32 TRIG 输出电平 vs 激光 TTL 输入门限——实物示波器确认，定是否加电平转换。
2. `readParams` 字段映射待实物回环验证后修正。
3. 激光仍未接入生产自启链路（`tof_viewer` 不在哪吒 systemd 自启中）——独立架构问题，另议。

### 2026-05-22 — 闭环开发方向确定 + ToF 雾分离算法原型（仿真验证）

**用户确定的系统愿景（主动调制感知闭环 + 数据驱动策略优化）：**
哪吒处理数据 → 给 RK3568 发指令调电机镜头 + 调激光 → 激光调制增强目标/雾分离
→ 所有数据（含**原始直方图**）上云做深度学习 → 优化调节策略，使闭环更快更稳。
**5G 上云维持暂缓**，先把闭环本体跑通。

**架构决策：**
- **激光接哪吒**（理由：PF32 TRIG 同步线要求激光器与 PF32 物理靠近；激光闭环本地延迟最低；控制代码已在哪吒）。**电机维持接 RK3568**。
- 分工：哪吒 = 大脑 + 激光快回路；RK3568 = 电机慢回路（经 STM32）+ 屏显。
- 哪吒→RK 控制指令复用现有 SPI（同方向），加"帧类型"区分深度帧 / 控制帧。

**ToF 算法原型（`nezha/algorithm/`，Python，独立原型，未接入主链路）：**
- 确认 PF32 直方图 API 数据类型：`uint16[1024 像素 × 1024 bins]`，反向 start-stop（查旧 `FW_Histogramming.cpp` + `ExampleTOF.cpp`，权威）
- `tof_sim.py` 物理模拟器：目标峰（Beer-Lambert 双程雾衰减）+ 雾近距后向散射 + 泊松噪声，产出与真实 API 一致的 `uint16[32,32,1024]`
- `tof_process.py`：`depth_argmax()`（现有 C 端等价基线）vs `depth_separate()`（扣暗本底 + 散射包络扣除 + matched filter + find_peaks + 亚 bin）；指标 SBR / 峰显著性 / 质量分 Q
- `run_demo.py`：清空气/中雾对比 + 代表像素直方图 + 目标距离扫描（出 `out/*.png`）

**验证结果：**
- 清空气：argmax / 分离均 ~100% 命中（分离亚 bin RMSE 1.1mm）
- 中雾 4m：argmax 命中 **16%** → 分离 **96%**（RMSE 2.4mm）
- 距离扫描（中雾）三段：近距 2–3.6m 两法 100%；中距 4–5.2m argmax 97%→2% 而分离稳 100%（**算法价值区**）；远距 ≥5.6m 分离 94%→64%、argmax 全灭（**物理探测极限，需闭环加功率/调焦提 SNR**）

**结论：** 雾分离算法在中距有效；远距是物理极限，量化论证了主动调制闭环的必要性（闭环目标 = 把命中率随距离下降那条线往远推）。

**边界（重要）：** 主采集链路 `sim_pf32` / `ExampleTOF` / `peak_detect.h`（argmax）**保持不动**；新算法原型仅存档，本阶段不接入。

**待续：** 仿真跑通主动调制闭环（调焦/功率 → Q 爬山搜索）；分离去椒盐 + 雾散射 Gamma 拟合；真实 PF32 数据标定参数；验证后移植 `tof_process.py` → C。

### 2026-05-21 — 屏显部署修复 + 双机开机自启 + 开发环境文档

**用户要求：** 用 `~/rk3568_linux_sdk` 交叉编译修 Qt 屏显并部署 → 思考下一步 → 哪吒生产无网，配开机自启 → 排查重启后屏显异常 → 整理文件上传 GitHub

**做了：**
- **qt_display 交叉编译 + 部署**：用 `~/rk3568_linux_sdk/.../host/bin/qmake`（GCC 10.3.0 + Qt5.15.2）编译 aarch64 binary，paramiko SFTP/串口部署到 `/myApp/tof3/qt_display/`。屏显修复确认：**先蓝底绿块 fallback → 切真实深度图**（jet 热图实时刷新），I2 屏显问题闭环
- **哪吒 systemd 自启**（`nezha/autostart/`）：`tof-acquisition.service`（sim_pf32→/tmp/depth.dat）+ `tof-spi-syncer.service`（spi_syncer→/dev/spidev1.0，root，ExecStartPre 等 spidev/depth.dat 就绪）。修 ordering cycle（`After=multi-user.target`→`basic.target`）；禁旧 v1.0 crontab（`PF32dataAcquisitionAndSPIsend`）；**重启验证两服务 active、depth.dat seq 递增**
- **RK3568 禁用旧 v1.0 自启**（关键踩坑）：旧 `S51mydisplay`/`S99myspireceive` 之前改成 `.old` 后缀**并未禁用**——Buildroot `rcS` 用 `for i in /etc/init.d/S??*`，`.old` 仍以 S 开头仍匹配，照样 `$i start`，导致开机**三阶段闪屏**（旧 SinglePhoton 界面→qt 兜底→真实图）。改名为 `DISABLED.mydisplay`/`DISABLED.myspireceive`（去掉 S 前缀）才真正禁用，并 kill 残留旧 SinglePhoton207 进程
- **重启后"上白下黑"排查**：实测为哪吒重启后 spi_syncer 尚未推上首帧的暂态（weston/spi_receiver/qt_display 进程均正常，received.dat magic TOFP 正确），数据上来即自愈
- **文档**：新增 `docs/开发环境.md`（两机地址/SDK/快速连接/链路启动序/踩坑）；更新 `docs/登录方式.md`（哪吒 IP 192.168.31.127→**192.168.31.79**，DHCP/MAC 标注）

**验证：** 屏显＝用户目视真实深度图实时刷新 ✅；哪吒自启＝重启后两 service active + depth.dat seq 递增 ✅；RK 自启＝重启后仅 weston+spi_receiver+qt_display，旧 SinglePhoton 消失，开机不再出旧界面 ✅

**遗留：**
1. qt_display 启动瞬间仍会闪一下蓝底绿块兜底（首帧未到）；如需消除可改为收到首帧再 `showFullScreen`
2. acquisition 当前跑 sim_pf32 模拟器；接真实 PF32 后改 `tof-acquisition.service` 的 ExecStart
3. `deploy/` 下一次性诊断脚本（check_*/diag_*/step[1-4]_* 等）可清理，待定

### 2026-05-19 — P-RT 二轮联调（清现场 + USB reset + QPA 定位 + 仓库整理）

**用户要求：** 清现场重做 → 思考 I1/I2 原因与解法 → 以"球状突出"图为例传到 3568 并 Qt 显示 → 黑屏后更新 md + 整理目录 + 推 GitHub

**做了：**
- 清两机残留（哪吒 sim_pf32/spi_syncer；RK3568 旧 wedged spi_receiver/qt_display）
- 三件套全部重新交叉编译 + 重部署（板上二进制曾丢失）：spi_syncer(x86_64)/spi_receiver(aarch64)/qt_display(aarch64)，md5 校验一致
- **I1**：根因＝USB-SPI 适配器（CDC-ACM，sysfs `2-1`）USB 层 wedge（设备号反复递增佐证）；
  验证有效复位手段＝`unbind`/`bind` sysfs 端口强制重枚举（与控制台 CH340 不同端口，安全）。未内置进 spi_receiver 重连
- **数据链路 USB reset 后再次端到端实测通过**：received.dat 2070B/TOFP，seq 564→590→830 持续递增
- **I2**：定位旧 app（`S51mydisplay` → `. /etc/profile` → `/etc/profile.d/weston.sh`）实为
  `QT_QPA_PLATFORM=wayland`+`XDG_RUNTIME_DIR=/var/run` 的 **Weston wayland 客户端**（非 linuxfb，纠正旧文档）。
  用对平台后 qt_display 进程稳定不崩、连上 Weston、无 QPA 错——**但用户目视仍黑屏**：进程层修复但无可见输出，I2 未解（更深层）
- 仓库整理：补 `.gitignore`（新目录二进制/qmake 生成物）、清构建产物、提交源码+脚本+文档推 GitHub

**验证：** 数据链路＝received.dat 字节/seq 实测通过；屏显＝用户目视黑屏（**未声称修复**）

**遗留：** I2 黑屏更深层排查（窗口 map/几何/重绘/wayland buffer，候选见 plan §9.6.3）；I1 USB reset 内置自动化；S95/S96 自启与旧自启切换

### 2026-05-20 — 屏显黑屏多轮排查（中间状态，05-21 收口）

> 多次试错日，最终结论看 2026-05-21 屏显部署修复条目。本日主要中间动作：
> - I2 黑屏定位为 weston/qt_display 时序（不是渲染逻辑）；手动启动 weston + 合成帧目视红/蓝渐变热图 OK
> - Qt 源码改 FramelessWindowHint + 延迟 showFullScreen()；移除 QMainWindow 全局黑底 stylesheet；depthWidget 加 WA_OpaquePaintEvent
> - autostart S95 加 `rmmod cdc_acm` 防 USB-SPI 适配器被抢占；S96 加 `wait_for_weston` socket 等待
> - 新增 `deploy/setup_spidev.sh`、`deploy/spi_e2e_test.py`、`deploy/e2e_test.py`
> - 哪吒 SSH 间歇不通（22/24/2222 等），多次只能走串口部署
> - qt_display 起 wayland 失败回退 linuxfb，屏幕仍闪黑——根因次日才确认

### 2026-05-19 — 联调连通 + 架构锁定 + 全项目文档重写

**用户锁定决策：**
- RK3568 屏幕**实时 Qt MIPI 显示深度图**（硬需求）
- 深度帧（2KB）走 **SPI 实时流**；原始 TCSPC（2MB）**只哪吒本地存档**
- **5G 上云（raw+depth）本阶段暂缓**，日后稳定再加；cloud_syncer 保留不动
- 哪吒生产无网（当前网线仅调试）；电机 RK3568 直连 STM32 串口

**实测/验证：**
- 哪吒 SSH 通（paramiko，无 sshpass）；RK3568 串口通（CH340 须慢写，否则丢首字节致 `Done(127)`）
- **SPI 物理链路哪吒原生引脚→USB-SPI 适配器(0483:5740)→RK3568 实测逐字节通**：哪吒旧 `spisendfile0402` 发 `raw.dat`，RK3568 旧 `spi_rev_slavemyloop` 收，received.dat 头部逐字节一致（md5/大小差为旧文本协议分帧尾差，非传输损坏）
- RK3568 5G 插 SIM 冷启动后注册联网（暂缓接入）
- 关键带宽事实：原始 14GB/h 受哪吒→RK SPI ~50–140KB/s 卡死，全量自动上云物理不可行

**文档重写（仅文档，不动代码）：**
- `ARCHITECTURE.md`、`CLAUDE.md`、`docs/rk3568_framework.md` 按锁定决策重写
- `rk3568/README.md` 及 spi_receiver/cloud_syncer/motor_controller/autostart 各 README 同步
- `docs/rk3568_reintegration_architecture.md` 横幅补新推翻项
- 新增 `docs/登录方式.md`、`docs/spi硬件接口.md`
- 旧"RK3568 不做显示/SPI 不做实时流/哪吒无网必经 SPI→5G 上云"表述全部更正

**风险/遗留：**
- 实时显示链路（哪吒 SpiSyncer + RK3568 spi_receiver + Qt 显示）三块未写，本阶段核心
- STM32 接 RK3568 哪个 /dev 节点未定（开放项 O2）
- SPI 链路验证用的是旧文本协议；TOF3.0 二进制深度帧协议（CMD0x10）细节待定（O4）

### 2026-05-19 — cloud_syncer 深度上传实现 + 离线 e2e

**用户确认：** 先做深度上传（D1=A 本地状态库续传；TCSPC 本轮不做）

**实现内容（`rk3568/cloud_syncer/`，Python 3.8 仅标准库）：**
- `config.py` 命令行/环境变量配置（不硬编码）
- `tof_parser.py` 解析 `.tof`（头 `TOFREC1\0` + 2062B/帧，与 datarecorder 一致）
- `state_db.py` sqlite 断点续传/幂等（仅 accepted 后推进 units_sent）
- `uploader.py` urllib POST `/api/frames/depth` + health；区分可重试/致命错误
- `buffer_scanner.py` 选完整 `.tof`（跳 `.part`/`.bad`）+ 坏文件隔离
- `status_writer.py` 原子写 `.upload_status.json`（供 spi_receiver 发 CMD=0x05）
- `cloud_syncer.py` 守护循环 + 信号 + 日志滚动；`sync_pass()` 可测试
- `tests/`：合成 `.tof` 生成器 + stdlib mock 云端 + e2e 脚本

**验证：** `python3 tests/test_e2e.py` —— 3 场景 14 项断言**全过**：
全量 137 帧上传、断网中断后续传（无重复/不丢帧，验证 D1=A 正确性）、坏文件隔离。
`py_compile` 全模块通过。本机 Python 3.10，已按 3.8 兼容写（仅标准库）。

**风险/遗留：**
- 仅 mock 云端验证，未对真实 FastAPI / RK3568 / 5G 联调（板上无网络、无 SIM）
- D1=A 残留：POST 成功但响应丢失时最多 1 个 batch 可能重复（设计内可接受）
- net_manager 未接入，暂用 `/api/health` 自探；与 spi_receiver 落盘/状态联调待做

### 2026-05-19 — 全项目梳理 + RK3568 框架定稿 + 修明显 bug

**用户确认决策：**
- SPI 接收：沿用 **USB转SPI 适配器**（旧版已验证，绕开原生 SPI 设备树问题）
- 电机控制：**RK3568 直连 STM32 串口**（19200 8N1，非经 SPI CMD=0x06，非留哪吒）
- 本轮范围：梳理 + 决策文档 + 修明显 bug，不写大块新实现

**实现内容：**
- 新增 `docs/rk3568_framework.md`（RK3568 侧权威框架：目录结构/模块/数据流/协议/部署/开放项/缺口）
- 搭建 `rk3568/` 骨架：`README.md` + `spi_receiver`/`cloud_syncer`/`motor_controller`/`autostart` 各模块设计 README
- 修正全项目文档架构矛盾（按确认决策）：
  - `CLAUDE.md`：SPI 链路改 USB转SPI；废弃 CMD 0x06；电机归属/STM32 连接更正；新增框架文档指引
  - `ARCHITECTURE.md`：硬件拓扑/SPI 物理层/CMD 表/电机焦距控制更正 + 顶部已确认决策提示
  - `docs/rk3568_reintegration_architecture.md`：顶部加"已被推翻/留档"横幅（原文两处自相矛盾）
- 修 `nezha/qt_app/motoruart.cpp` 协议 bug：
  - 第 6 字节由硬编码 `0x00` 改为校验和 `(0x02+device+cmdHi+cmdLo)&0xFF`
  - 齿轮指令 cmdHi 由错误的 `0x20/0x22`（滑台值）改为 `0x40/0x42`
  - 已与 STM32 串口指令文档/旧版 `motor.cpp` 全表逐条核对一致

**验证：**
- 文档改动：人工核对，无构建依赖
- `motoruart.cpp`：本机无 Qt5（开发机），无法本地编译；改动为常量算术 + 数组初始化，无 API/头文件变化，风险低；需在哪吒 `qmake && make` 验证（见 AGENTS.md 部署流程）

**风险/遗留：**
- `libUSB2UARTSPIIIC.so`（aarch64/x86_64）与已编译 `spi_rev_slavemyloop` 仅在 `单光子项目`，未拷入 TOF3.0（框架文档 §7 已记录为缺口）
- 电机闭环控制通道为开放项 O1（框架文档 §6）
- motoruart 校验和修正未经真实 STM32 回环验证，仅与协议文档核对

### 2026-05-18 — TOF3.0 项目初始化与目录重组

**实现内容：**
- 从 TOF2.0 迁移所有代码到 TOF3.0，保留 TOF2.0 不动
- 复制 `refs/`（PF32 手册、RK3568 文档）
- 复制 `rk3568/legacy/`（v1.0 电机 / SPI 参考代码）
- 按设备分层重组目录：
  - `acquisition/` → `nezha/acquisition/`
  - `qt_app/` → `nezha/qt_app/`
  - `ml/` → `cloud/ml/`
  - 新增 `rk3568/spi_receiver/`、`rk3568/cloud_syncer/`（占位）
- 更新 ARCHITECTURE.md、CLAUDE.md、AGENTS.md 所有路径
- 更新 `deploy/` 下 4 个脚本的本地/远程路径（TOF2.0→TOF3.0）
- 新增 `docs/rk3568_connection.md`（串口连接与硬件现状）
- 编写算法文档：
  - `docs/active_modulation_separation_algorithm.md`
  - `docs/rk3568_reintegration_architecture.md`

**已提交 commits：**
- `init: TOF 3.0 项目初始化`
- `refactor: 按设备分层重组目录结构 nezha/rk3568/cloud`

### 2026-05-18 — 哪吒侧（继承自 TOF2.0，已验证）

- `nezha/acquisition/sim_pf32.cpp` — 帧模拟器，~2Hz
- `nezha/qt_app/tof_viewer` — Qt 主程序，HDMI 显示
- `cloud/server/main.py` — FastAPI 4 端点，8765 端口
- CloudSyncer SQLite 队列，DataRecorder 本地录制

---

## 关键决策记录

| 时间 | 决策 | 原因 |
|------|------|------|
| 2026-05-18 | RK3568 回归，作为 5G 上行网关 | 哪吒无网络，RK3568 有 5G 模块 |
| 2026-05-18 | 电机控制迁移到 RK3568 | 有专用电机驱动引脚，复用 v1.0 代码 |
| 2026-05-18 | SPI 改为文件队列异步传输 | 避免实时流 SPI 不稳定 |
| 2026-05-18 | 主动调制分离算法思路 | 焦距/功率差分区分雾目标，文献无此方法 |
| 2026-05-18 | RK3568 侧优先用 Python 实现 | 板上无 gcc，Python 3.8 可用，无需交叉编译 |
| 2026-05-19 | SPI 接收用 USB转SPI 适配器（非原生 SPI） | 旧版已验证；绕开 fe620000 被 STM32 占用、其余 disabled 的设备树阻塞 |
| 2026-05-19 | 电机 RK3568 直连 STM32 串口（非 SPI CMD=0x06） | 沿用旧版 motorUart 已验证思路；SPI 仅文件队列，不承载实时控制 |
| 2026-05-19 | spi_receiver 走交叉编译（非纯 Python） | 需复用 aarch64 `libUSB2UARTSPIIIC.so` + 二进制帧解析；cloud_syncer/motor 仍 Python |
| 2026-05-19 | **RK3568 实时 Qt MIPI 显示深度图** | 用户硬需求；v1.0 已在板上跑过 Qt 显示 |
| 2026-05-19 | **深度帧走 SPI 实时流**（推翻"不做实时流"） | 2KB 帧带宽富余；当年坏的是 2MB 原始，非 SPI 本身 |
| 2026-05-19 | **原始 TCSPC 只哪吒本地存档** | 14GB/h 受 SPI ~50–140KB/s 卡死，全量自动上云不可行 |
| 2026-05-19 | **5G 上云本阶段暂缓** | 先打通实时显示；cloud_syncer 已就绪日后接 |

---

## 下一步工作计划

### 本阶段（已完成或在跑）

| 状态 | 任务 |
|------|------|
| ✅ | 实时显示链路 哪吒 SpiSyncer → SPI → RK3568 spi_receiver → Qt MIPI 屏显（已端到端实测通过，21 号收口） |
| ✅ | 双机开机自启 systemd + S95/S96，旧 v1.0 已禁用 |
| ⏸️ | 5G 阶段：net_manager + cloud_syncer 接真实云 + 哪吒批量上行 + TCSPC 端点（cloud_syncer 已实现+e2e，保留不动） |
| 🟡 | motor_controller（RK3568 串口下发 STM32），开放项 O2 节点待定 |

### 算法研究主线（research/，Phase A）

| 状态 | 任务 |
|------|------|
| ✅ | Phase A baseline：5 算法实测，loader F-order bug 已修，verify_baseline.md 沉淀 |
| ✅ | research/ 中文五段式头注释 + `docs/research_code_style.md` 规范沉淀 |
| 🟡 | `lmf.py` 换数据集自带真 IRF（`research/datasets/PSF_64x64.mat`）替代 Gaussian 近似 |
| 🟡 | 接入 `tail_bg_argmax` 到 run_sanity，跑 5 样本均值 |
| 🟡 | `run_verify_baseline.py` 加 `lmf_spad` / `spatial_3x3` 列 |
| 🟢 | Phase B：雾注入对比、ML 训练（按 `algorithm_research_roadmap.md`） |

---

## 待确认事项（未解决）

| 问题 | 状态 |
|------|------|
| STM32 接 RK3568 哪个 /dev 节点 | 🔴 开放项 O2，待硬件接线 |
| 电机闭环控制通道 | 🟡 开放项 O1，当前默认本地手动 |

> 已解决的（SPI 物理链路、5G 注册、二进制协议、SpiReceiver 进程模型、交叉编译器版本）见
> 上方"当前状态快照"或 `docs/rk3568_framework.md`。

---

## 文件变更追踪（仅未完结/待办）

| 文件 | 状态 |
|------|------|
| `rk3568/motor_controller/motor_ctl.py` | ⬜ 待开放项 O2 接线确认 |
| `rk3568/cloud_syncer/` 全部 | ⏸️ 已实现+e2e，归暂缓阶段保留不动 |
| `cloud/server/main.py` POST /api/frames/tcspc | ⏸️ 5G 阶段再加 |
| `research/algorithms/lmf.py` | 🟡 换真 IRF 替代 Gaussian 近似 |
| `research/algorithms/tail_bg_argmax.py` | 🟡 接入 run_sanity，跑 5 样本均值 |
| `research/run_verify_baseline.py` | 🟡 加 `lmf_spad` / `spatial_3x3` 列 |

> 已完成的实时显示链路 / 自启 / SPI 协议 / 文档重写等文件，状态见上方"当前状态快照"，
> 不再在此重复列出。

<!-- 2026-05-20 屏显排查、spidev 诊断、现网联调三条已并入上面"05-20 屏显黑屏多轮排查"
     和文件变更追踪表，避免重复。所有结论在 2026-05-21 屏显部署修复中收口。 -->
### 2026-05-27 — Phase A 算法研究流水线落地

Codex worker 在原 `nezha/algorithm/`（后迁 `research/`）完成：
- `sim_spad_loader.py` 支持 sparse `spad`、raw `bin` GT、`bin_size_ps`、intensity、数据集自带估计字段
- 加 `contracts.py`、`argmax` baseline、`eval/metrics.py`、`eval/viz.py`、`run_sanity.py`
- `tests/test_phase_a.py` 回归测试通过；`out/`/`datasets/`/`runs/` 入 `.gitignore`

> ⚠️ **本日报告中的"argmax hit_rate ≈ 8.6% / RMSE ≈ 2869mm"已过时**：
> 那是 loader F-order bug 时期的错误数字（行列被转置）。
> 05-28 修复 `reshape(..., order="F")` 后，5 样本均值 hit@200mm = **0.579**
> ≈ 数据集自带 `ds_argmax` 0.580。实测见 `research/out/verify_baseline.md`。
