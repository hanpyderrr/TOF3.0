# motor_controller — 镜头调焦电机控制

完整设计见 [`docs/rk3568_framework.md`](../../docs/rk3568_framework.md) §3.3。

## 链路

RK3568 `/dev/ttyS4` → STM32F103（板内）→ TMC2209 ×2（板内）→ 镜头电机（滑台调焦 + 齿轮光圈）

> 改版底板 STM32 + TMC2209 ×2 **板上焊死**，电机接 MOTOR1 / MOTOR2 接线柱。
> 全板 UART 映射、跳线、激光等参考 [`docs/board_custom_uart_mapping.md`](../../docs/board_custom_uart_mapping.md)。

## 串口协议

- 串口：**`/dev/ttyS4`**，19200 8N1（UART4 M1 pinmux；JP2 跳线短接 3-5/4-6，对接 STM32 USART1）
- 帧：`0xFF 0x02 [device] [cmdHi] [cmdLo] [checksum]`（6 字节）
- checksum = `(0x02 + device + cmdHi + cmdLo) & 0xFF`
- device：`0x01`=滑台(调焦) `0x02`=齿轮(光圈)
- cmdHi：前/顺 滑台`0x20` 齿轮`0x40`；后/逆 滑台`0x22` 齿轮`0x42`
- cmdLo：`0x01`=粗调 `0x02`=细调

指令全表：

| 动作 | 帧 |
|------|----|
| 滑台前进 粗/细 | `FF 02 01 20 01 24` / `FF 02 01 20 02 25` |
| 滑台后退 粗/细 | `FF 02 01 22 01 26` / `FF 02 01 22 02 27` |
| 齿轮顺时针 粗/细 | `FF 02 02 40 01 45` / `FF 02 02 40 02 46` |
| 齿轮逆时针 粗/细 | `FF 02 02 42 01 47` / `FF 02 02 42 02 48` |

协议来源：STM32 `电机调焦串口指令` 文档 + 旧版 `../legacy/服务器代码/SinglePhotonContestServer_5/motor.cpp`。
STM32 固件参考：`../legacy/.../STM32F103_lensfocus_TMC2209`（不在 TOF3.0 改动范围）。

## 决策与开放项

- 语言：Python 3.8（板上自带）
- 电机当前为 RK3568 **本地/手动**控制，与哪吒 `FeedbackController` 解耦
- 开放项 O1/O3（框架文档 §6）：闭环控制通道、本地触发入口待定
- ~~开放项 O2~~ **已关闭（2026-05-29）**：STM32 串口节点 = `/dev/ttyS4`

## 缺口

- `motor_ctl.py` 待实现
- 哪吒侧 `nezha/qt_app/motoruart.{h,cpp}` 为过渡期实现，最终迁移到本模块后从哪吒构建移除
