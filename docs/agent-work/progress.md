# 工作进度

> 最后更新：2026-05-25
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
| ToF 雾分离算法原型 | ✅ `nezha/algorithm/` 仿真验证（中雾 4m：argmax 16%→分离 96%）；**独立原型，未接主链路** |

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

### 2026-05-20 — I2 黑屏根治 + autostart 修复 + e2e 脚本

**用户要求：** 按解耦思路排查 I2 黑屏，先确认显示层，再接数据层

**做了：**
- **I2 黑屏已根治** ✅：手动起 weston → 写合法 TofFrame 合成帧 `/tmp/received.dat`（base64 串口传入） → 起 qt_display；用户目视 **红/蓝渐变热图** 正常显示。根因=weston 没有随 qt_display 一起重启（wayland-0 是僵尸 socket），而不是渲染逻辑问题
- 诊断过程：qt.qpa.wayland 日志确认 Qt 已连上 weston 并持续 flush 1920×1080 buffer（`handleUpdate` 可见），`libQt5WaylandClient.so` 已 map，`/dev/dri/card0` + `/dev/mali0` 均已打开
- **S95tof_spi_receiver** 新增 USB adapter reset（unbind 2-1 / bind 2-1）
- **S96tof_display** 新增 `wait_for_weston()` 循环（等 wayland-0 socket 最多 10s），防止 qt_display 在 weston 就绪前启动
- **deploy/e2e_test.py** 新建：SSH 哪吒 + 串口 RK3568；检查 spidev1.0、启 sim_pf32 + spi_syncer、USB reset + spi_receiver、轮询 received.dat mtime；支持 `--display-only` / `--no-spi` 选项
- 哪吒 IP 确认：192.168.31.127（wlo1 wireless，DHCP；当前 SSH 正常）

**验证：** 用户目视红/蓝渐变热图 ✅；autostart 修改已写入源码未部署到板上

**遗留：**
1. 哪吒 `/dev/spidev1.0` 仍不存在（SSH 超时未完成诊断，需下次运行 `deploy/setup_spidev.sh` 确认原因）
2. `deploy/e2e_test.py` 未实测（spidev 未通则 SPI 链路测试会 skip）
3. 新 autostart 脚本（S95/S96）未部署到 RK3568 的 `/etc/init.d/`（需 serial 传入并 chmod +x）
4. `S51mydisplay`（旧）还在，需要禁用或替换

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

### 优先级排序（本阶段：打通实时深度显示链路）

| 优先级 | 任务 | 在哪做 | 依赖 |
|--------|------|--------|------|
| 🔴 | 补缺口：拷 `libUSB2UARTSPIIIC.so`(aarch64/x86_64)+头文件 入 `rk3568/spi_receiver/deps/` 与 `rk3568/legacy/lib/`（板上 /lib 已有可取） | 本地 | 无 |
| 🔴 | 定二进制深度帧协议细节（MAGIC/CMD0x10/CRC32，开放项 O4） | 本地 | 无 |
| 🔴 | 哪吒 SpiSyncer：算法出帧 → 低延迟推 `/dev/spidev1.0`（需 root） | 哪吒 | 协议定 |
| 🔴 | RK3568 spi_receiver：传输层照搬 0411.c + 二进制深度帧解析 → 交叉编译 | SDK 机 | 缺口+协议 |
| 🔴 | RK3568 Qt 显示程序：消费 TofFrame → MIPI 屏渲染 → 交叉编译 | SDK 机 | spi_receiver |
| 🟡 | 实时链路联调（哪吒发→RK 收→MIPI 屏显） | 两机 | 上述 |
| 🟡 | motor_controller（Python 串口下发） | 板上 | 开放项 O2（节点待定） |
| 🟡 | autostart（spi_receiver + Qt 显示） | 板上 | 上述实现 |
| ⏸️ | 【暂缓】5G 阶段：net_manager + cloud_syncer 接真实云 + 哪吒批量上行 + TCSPC 端点 | — | 系统稳定后 |
| 🟢 | P9 物理算法层 / P10 ML 训练 | 哪吒/云 | 真实数据 |

> 详细实施顺序见 `docs/rk3568_framework.md` §8。

### RK3568 SpiReceiver 开发方案

> 方案已定稿，详见 `docs/rk3568_framework.md` §3.1 / §8。要点：
> RK3568 是 **aarch64**，已编译的 `spi_rev_slavemyloop` 与 `libUSB2UARTSPIIIC.so` 均为 aarch64。
> 因需在传输层（OpenUsb/ConfigSPIParamSlave/SPISlaveRcvData）之上新增二进制组帧，
> 须在 SDK 机用 `aarch64-linux-gnu-gcc` 链接 aarch64 `libUSB2UARTSPIIIC.so` 交叉编译，
> 产物经串口 base64 传到板上。**不可纯 Python**（须链接厂商 .so）。

### 串口传输文件方法（无网络时）

```bash
# 在开发机：base64 编码
base64 binary_file > binary_file.b64

# 在串口 shell 中：
base64 -d binary_file.b64 > binary_file
chmod +x binary_file
```

---

## 待确认事项

| 问题 | 状态 |
|------|------|
| 哪吒↔RK3568 SPI 物理链路 | ✅ 实测逐字节通（USB转SPI 适配器 0483:5740） |
| SIM 卡 / 5G | ✅ 已插，冷启动注册联网；本阶段暂缓接入 |
| 二进制深度帧协议细节（MAGIC/CMD0x10/CRC32、是否用 INT 线、丢帧策略） | 🔴 开放项 O4，本阶段需先定 |
| STM32 接 RK3568 哪个 /dev 节点 | 🔴 开放项 O2，待用户确认接线 |
| spi_receiver 与 Qt 显示进程模型（合一/拆分） | 🟡 开放项 O6，实现时定 |
| 电机闭环控制通道（开放项 O1） | 🟡 当前默认 RK3568 本地/手动 |
| aarch64 交叉编译器（aarch64-linux-gnu-gcc）版本 | ⬜ 待确认（本机 rk3568_linux_sdk 内 Linaro 6.3.1 应匹配） |

---

## 文件变更追踪

| 文件 | 最近变更 | 状态 |
|------|---------|------|
| `nezha/qt_app/mainwindow.cpp` | Record 面板 UI | ✅ 已部署 |
| `nezha/qt_app/cloudsyncer.cpp` | SQLite 队列实现 | ✅ 已部署 |
| `cloud/server/main.py` | FastAPI 4 端点 | ✅ 运行中 |
| `ARCHITECTURE.md` | 按 3.0 双机架构重写 | ✅ |
| `CLAUDE.md` | 路径/架构全面更新 | ✅ |
| `AGENTS.md` | 更新为 TOF3.0 内容 | ✅ |
| `deploy/*.py` | 路径更新 TOF2.0→TOF3.0 | ✅ |
| `docs/rk3568_connection.md` | 补 Linux 连接(termios) + readline 自动化限制 | ✅ |
| `docs/rk3568_framework.md` | 新增 RK3568 权威框架文档 | ✅ 2026-05-19 |
| `rk3568/README.md` + 各模块 README | 目录骨架与模块设计 | ✅ 2026-05-19 |
| `CLAUDE.md` / `ARCHITECTURE.md` | 修正 SPI/电机架构矛盾 + 框架指引 | ✅ 2026-05-19 |
| `docs/rk3568_reintegration_architecture.md` | 加"已被推翻/留档"横幅 | ✅ 2026-05-19 |
| `nezha/qt_app/motoruart.cpp` | 修协议 bug（校验和 + 齿轮 cmdHi） | ✅ 2026-05-19 待哪吒编译验证 |
| `cloud/server/main.py` | 加 POST /api/frames/tcspc | ⬜ P9-1 |
| `rk3568/spi_receiver/spi_receiver.c` | 传输层 + 二进制组帧实现 | ⬜ 下一步 |
| `rk3568/spi_receiver/deps/` | 拷入 .h + aarch64/x86_64 .so | ⬜ 缺口 |
| `rk3568/cloud_syncer/*.py` | 深度上传实现（7 模块 + tests） | ✅ 2026-05-19 离线 e2e 通过 |
| `rk3568/cloud_syncer/` 全部 | 已实现+e2e；归暂缓阶段保留不动 | ⏸️ 暂缓 |
| `docs/cloud_syncer_plan.md` | 代码计划 + 决策 | ✅ 2026-05-19 |
| `rk3568/motor_controller/motor_ctl.py` | 串口下发电机指令 | ⬜ 待 O2 |
| `ARCHITECTURE.md` / `CLAUDE.md` / `docs/rk3568_framework.md` | 按锁定决策重写（实时显示/实时流/raw 本地/5G 暂缓） | ✅ 2026-05-19 |
| `rk3568/README.md` + spi_receiver/cloud_syncer/motor/autostart README | 同步锁定决策 | ✅ 2026-05-19 |
| `docs/登录方式.md` / `docs/spi硬件接口.md` | 新增（两机登录 + SPI 硬件接口+实测） | ✅ 2026-05-19 |
| `docs/rk3568_reintegration_architecture.md` | 横幅补新推翻项 | ✅ 2026-05-19 |
| `nezha/spi_syncer/` (spi_syncer.c+Makefile+README) | 实时深度发送端，移植 spisendTOF+seq 去重 | ✅ 2026-05-19 x86_64 编译+联调过 |
| `rk3568/spi_receiver/` (spi_receiver.c+Makefile+deps+README) | SPI slave→/tmp/received.dat，SIGHUP-ignore | ✅ 2026-05-19 aarch64 交叉+联调过 |
| `rk3568/qt_display/` (main/mainwindow/depthParser/depthWidget+.pro) | Qt MIPI 显示，wayland 客户端 | ✅ 编译+部署；⚠️ 屏显黑屏未解(plan §9.6) |
| `rk3568/autostart/S95tof_spi_receiver`+`S96tof_display` | BusyBox init.d 自启（未安装） | ✅ 已写，未装 |
| `.gitignore` | 补新目录二进制/qmake 生成 Makefile·moc·.qmake.stash | ✅ 2026-05-19 |
| `nezha/qt_app/cloudsyncer.*` | 维持本地开发用，不改 | — |

### 2026-05-20 — Qt 源码修复（fullscreen + 渲染）+ 交叉编译准备

**用户要求：** 分析黑屏+非全屏+颠倒原因，Codex 给出代码修复

**做了：**
- 确认板上 binary 为 aarch64 ELF（`file` 命令串口验证），正点原子 gnueabihf 工具链不兼容，需在有 SDK 的 Linux 机器交叉编译
- **rk3568/qt_display/main.cpp**：新增 `Qt::FramelessWindowHint`，通过 `QTimer::singleShot(0,...)` 延迟 `showFullScreen()`，解决 Wayland compositor 未处理 fullscreen 请求的时序问题（xdg_toplevel configure 返回 WindowNoState）
- **rk3568/qt_display/mainwindow.cpp**：移除 `setStyleSheet("background:#000;")` QMainWindow 全局 stylesheet（Wayland/EGL 下会级联覆盖子 widget 绘制），改为 central widget palette 黑底
- **rk3568/qt_display/depthWidget.cpp**：构造函数增加 `setAutoFillBackground(false)`、`WA_OpaquePaintEvent`、`WA_NoSystemBackground`，声明 widget 为自绘不透明
- **rk3568/autostart/S95tof_spi_receiver**：`usb_adapter_reset()` 头部加 `rmmod cdc_acm 2>/dev/null || true`，防止内核 cdc_acm 驱动抢占 USB adapter（0483:5740）导致 libusb OpenUsb=-1
- 确认 weston.ini `transform=rotate-90` 可能需改 `rotate-270` 解决颠倒（待交叉编译部署后板上验证）
- 新增 `docs/cross_compile_qt_display.md`：SDK 机交叉编译 + 串口部署 + weston.ini transform 调试完整步骤

**状态：** 源码修改已入库，**尚未交叉编译部署**。需在有 aarch64 SDK 的 Linux 机器 `git pull` + `qmake` + `make` + 串口传板。

**验证方式：** 见 `docs/cross_compile_qt_display.md`

**遗留：**
1. 交叉编译并部署新 qt_display binary 到 RK3568 `/myApp/tof3/qt_display/qt_display`
2. 验证 fullscreen configure（串口看 weston 日志不再出现 WindowNoState）
3. 验证蓝底绿块 fallback 上屏（无帧时应可见）
4. 测试 weston.ini transform `rotate-270` 是否修正颠倒
5. 哪吒 spidev1.0 仍待诊断（SSH 超时）

### 2026-05-20 - spidev 诊断、RK3568 黑屏日志增强、SPI e2e 脚本

- 新增 `deploy/setup_spidev.sh`：哪吒本机执行，诊断 ACPI/LPSS/SPI 控制器，尝试 `modprobe spidev`，枚举 `/dev/spidev*`，缺节点时通过 sysfs 创建/绑定。
- 修改 `rk3568/qt_display/main.cpp`：启动时打印 frame path、QPA platform、screen geometry，并改为 `showFullScreen()`。
- 修改 `rk3568/qt_display/mainwindow.cpp`：轮询 `received.dat` 时打印读失败、重复 seq、新帧 seq/valid 日志。
- 修改 `rk3568/qt_display/depthWidget.cpp`：`paintEvent` 周期性打印日志；未收到深度帧前绘制蓝底绿块 fallback，用于确认窗口实际上屏。
- 新增 `deploy/spi_e2e_test.py`：SSH 哪吒启动 `sim_pf32` 和 `spi_syncer`；串口 RK3568 做 USB-SPI reset、启动 `spi_receiver`，可选启动 `qt_display`，轮询 `/tmp/received.dat` 并校验 magic/version/尺寸/validCount/depth range/CRC16。
- 本地验证：`python -m py_compile deploy/spi_e2e_test.py` 通过。当前 sandbox 无 `qmake`/`bash`，Qt 交叉构建、shell `bash -n`、真实硬件链路未在本机执行。

### 2026-05-20 - RK3568 现网联调结果

- 哪吒侧：`192.168.31.127` 可 ping，但 `22/24/2222/2200/8022` 都不通，当前这台开发机无法直接 SSH 上去执行 `spidev` / `spi_syncer`。
- RK3568 侧：`COM7 @ 1500000 8N1` 可连通，板上返回 `Linux ATK-DLRK3568 4.19.232 aarch64`，串口链路正常。
- USB-SPI 适配器：板上可见 `0483:5740`，执行 USB unbind/bind 后枚举出 `2-1`，`spi_receiver` 进程可启动。
- 显示进程：`qt_display` 已启动，先后尝试 `wayland` 和 `linuxfb`，`wayland` 因 `wl_display` 不存在失败，`linuxfb` 可以起来。
- 当前屏幕表现：用户现场看到的是“闪烁黑屏 + 没有数据的窗口”；从日志侧看，`qt_display` 进程在跑，但还没有确认到有效深度帧刷新到屏幕上。
- 当前文件状态：`/tmp/received.dat` 目前未由哪吒端持续刷新，`spi_receiver` 只看到 `nohup: ignoring input`，说明接收端进程在但上游数据链路还没打通。
