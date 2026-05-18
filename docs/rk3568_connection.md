# RK3568 连接方式与硬件现状

> 记录时间：2026-05-18
> 状态：串口已通，无网络

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

| 项目 | 值 |
|------|-----|
| 接口 | USB-UART CH340 → Windows COM7 |
| 线材 | USB 转 Type-C（直接接板子调试口） |
| 波特率 | **1500000**（1.5M baud） |
| 数据位 | 8N1 |
| 登录状态 | 开机自动进入 root shell，无需登录 |

### Python 连接示例

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
