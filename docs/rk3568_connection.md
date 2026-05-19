# RK3568 连接方式与硬件现状

> 记录时间：2026-05-18
> 状态：串口已通（Windows COM7 与 Linux `/dev/ttyUSB0` 均已实测连通），无网络

---

## 硬件信息

| 项目 | 详情 |
|------|------|
| 板型 | ATK-DLRK3568（正点原子开发板） |
| 系统 | Buildroot Linux（非 Ubuntu） |
| 登录 | root，无密码 |
| 5G 模块 | Quectel RM500U-CNV |

---

## 串口连接

> 两种接入环境，**串口参数完全相同**（1500000 / 8N1 / raw），仅设备节点不同。

### 环境 A：Windows（历史记录）

| 项目 | 值 |
|------|-----|
| 接口 | USB-UART CH340 → Windows COM7 |
| 线材 | USB 转 Type-C（直接接板子调试口） |
| 波特率 | **1500000**（1.5M baud） |
| 数据位 | 8N1 |
| 登录状态 | 开机自动进入 root shell，无需登录 |

#### Python 连接示例（pyserial）

```python
import serial, time

s = serial.Serial('COM7', 1500000, timeout=3)
time.sleep(0.3)
s.read(s.in_waiting)  # drain boot output

def send(s, cmd, wait=1.5):
    s.write(cmd.encode() + b'\r\n')
    time.sleep(wait)
    return s.read(s.in_waiting or 2048).decode('utf-8', errors='replace')

print(send(s, 'uname -a'))
s.close()
```

### 环境 B：Linux 开发机（2026-05-18 已实测连通）

| 项目 | 值 |
|------|-----|
| 接口 | USB-UART CH340（`1a86:7523`）→ `/dev/ttyUSB0` |
| 波特率/帧 | **1500000**, 8N1, raw |
| 板子提示符 | `root@ATK-DLRK3568:/#`（root 无密码，开机自动进 shell） |
| 系统（实测） | `Buildroot 2018.02-rc3`，2024-08-29 编译，rockchip_rk3568_defconfig |
| 内核（实测） | `Linux 4.19.232 aarch64`，Linaro GCC 6.3.1，`#4 SMP 2025-01-13` |
| pyserial | **未安装**（板上有 `pip3`），用 Python 标准库 `termios`（见下） |
| 用户权限 | 操作用户需在 `dialout` 组 |

> 实测的 Buildroot 2018.02-rc3 / 内核 4.19.232 / aarch64 与 `docs/agent-work/progress.md` 记录**一致**（三者分别是发行版 / 内核 / 架构，并存不矛盾）。
>
> ⚠️ **远端 shell 自动化限制**：板子登录 shell 带 readline + bracketed-paste（提示符含 `\x1b[?2004h`），`stty -echo` 关不掉其输入回显，长命令会在 80 列处折行打乱解析。可靠做法：**单条短命令（命令行总长 <70 字符）+ 在返回内容里用唯一 marker 提取**；不要用 here-doc / 多命令批处理。

#### ⚠️ 关键坑（务必遵守，否则连不上）

- **必须用单一持久 fd 收发**：不要用 `cat` 或反复 `open()` 的方式。每次打开 CH340 都会翻转 DTR/RTS，反复开关会干扰/复位 RK3568，典型表现是"第一次收到几十字节错乱、之后任何波特率都 0 字节"。
- **`cflag` 必须清 `HUPCL`**：否则关闭端口时翻转 DTR，干扰下一次连接。
- 速率用 `termios.B1500000`（Linux 标准常量 = 4106；CH340 时钟 12MHz/8 整除，**速率本身是精确的**，错乱不是波特率问题，而是上面的开关端口问题）。

#### Python 连接示例（标准库 termios，无需 pyserial）

```python
import os, time, select, termios

fd = os.open('/dev/ttyUSB0', os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
a = termios.tcgetattr(fd)               # [iflag,oflag,cflag,lflag,isp,osp,cc]
a[0] = a[1] = a[3] = 0                   # raw: iflag/oflag/lflag
a[2] = (a[2] & ~(termios.CSIZE | termios.PARENB | termios.CSTOPB
                 | termios.CRTSCTS | termios.HUPCL)) \
       | termios.CS8 | termios.CLOCAL | termios.CREAD
a[4] = a[5] = termios.B1500000           # ispeed / ospeed
a[6][termios.VMIN] = 0
a[6][termios.VTIME] = 0
termios.tcsetattr(fd, termios.TCSANOW, a)
time.sleep(0.2)
termios.tcflush(fd, termios.TCIOFLUSH)    # 清掉开机/残留脏字节

def send(cmd):
    os.write(fd, cmd.encode() + b'\n')

def read(t=2.0):
    end, buf = time.time() + t, b''
    while time.time() < end:
        if select.select([fd], [], [], 0.2)[0]:
            buf += os.read(fd, 4096)
    return buf.decode('utf-8', 'replace')

read(1.0)                                 # drain
send('uname -a')
print(read())
os.close(fd)                              # 仅在整个会话结束时关闭
```

> 完整诊断脚本见 `/tmp/rkconn.py`（本机临时文件，未入库）。

---

## 网络现状（暂无网络）

| 接口 | 状态 | 原因 |
|------|------|------|
| eth0 | DOWN | DMA init 失败，未接网线 |
| eth1 | DOWN | 同上 |
| usb0 | NO-CARRIER | 5G CDC-NCM，无 SIM 卡 |

### 5G 模块状态

```
AT+CSQ    → +CSQ: 13,99   # 有信号（13 = 中等）
AT+CPIN?  → +CME ERROR: 10  # 未插 SIM 卡
AT+CEREG? → +CEREG: 0,0   # 未注册网络
```

5G AT 口：`/dev/ttyUSB2`，波特率 115200

---

## 恢复网络的方法（待操作）

**方案 A（推荐）：插 SIM 卡**
1. 关电，插 SIM 卡到 RM500U-CNV 模块的卡槽
2. 上电，等待注册（AT+CEREG? 返回 0,1 或 0,5）
3. 执行：`udhcpc -i usb0`
4. 拿到 IP 后配置 SSH，之后不再需要串口

**方案 B：接网线**
1. 接网线到 eth0 或 eth1
2. 执行：`udhcpc -i eth0`（或 eth1）
3. 同上，配置 SSH

---

## 当前可用的开发方式

串口 shell（COM7）是唯一通道，可以：
- 执行 shell 命令，编译运行 C/C++ 程序
- 通过 heredoc 向 `/tmp` 写脚本文件
- 读写 eMMC 上的文件系统
- 访问 5G 模块 AT 口（/dev/ttyUSB0-4）
- 访问 GPIO、SPI、CAN 等外设

**不能做的**：
- SSH / SCP 传文件（无网络）
- 大文件传输（串口 1.5Mbaud ≈ 150KB/s，实际更低）

---

## 相关文件路径

| 说明 | 路径 |
|------|------|
| SPI receiver 代码（待实现） | `rk3568/spi_receiver/` |
| Cloud syncer 代码（待实现） | `rk3568/cloud_syncer/` |
| v1.0 遗留代码参考 | `rk3568/legacy/` |
| SPI 协议设计文档 | `docs/rk3568_reintegration_architecture.md` |
