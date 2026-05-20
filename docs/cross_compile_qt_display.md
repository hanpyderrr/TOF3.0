# RK3568 qt_display 交叉编译指南

> 适用场景：修改了 `rk3568/qt_display/` 源码后，在有 SDK 的 Linux x86_64 机器上重新编译并部署到板上。

## 前提

- 机器上已有 `rk3568_linux_sdk`（Buildroot SDK，包含 aarch64-linux-gnu-gcc Linaro 6.3.1 + Qt 5.15.2 sysroot）
- 板上 binary 为 **aarch64 ELF**（已确认，正点原子 gnueabihf 工具链不兼容）
- 串口连接 RK3568（COM7 / `/dev/ttyUSB0`，1500000 8N1）

## 步骤

### 1. 拉取最新代码

```bash
cd ~/TOF3.0   # 或你的工作目录
git pull
cd rk3568/qt_display
```

### 2. 用 SDK 的 qmake 生成 Makefile

```bash
# 使用 SDK 内的 qmake（路径因安装位置而异）
~/rk3568_linux_sdk/buildroot/output/host/bin/qmake qt_display.pro

# 如果已 source SDK 环境脚本：
# source ~/rk3568_linux_sdk/buildroot/output/host/environment-setup
# qmake qt_display.pro
```

验证：`head -5 Makefile` 中 `CXX` 应指向 `aarch64-linux-gnu-g++`。

如果找不到 qmake 路径：
```bash
find ~/rk3568_linux_sdk -name qmake 2>/dev/null
```

### 3. 编译

```bash
make -j4
```

产物：`qt_display`（aarch64 ELF，约几百 KB）。验证：`file qt_display` 应显示 `ELF 64-bit LSB executable, ARM aarch64`。

### 4. 通过串口 base64 传到 RK3568

在有 Python + pyserial 的机器上，使用 `deploy/step4_rk_reboot.py` 中的 `upload_file()` 函数模式：

```python
# 参考 deploy/step4_rk_reboot.py 的写法
upload_file(s, "rk3568/qt_display/qt_display", "/myApp/tof3/qt_display/qt_display")
```

或单独写一个上传脚本，核心是 base64 分 60 字节块通过 `printf '%s'` 拼接，再 `base64 -d` 还原。

### 5. 板上重启 qt_display

通过串口执行：

```bash
killall qt_display 2>/dev/null; sleep 0.5
chmod +x /myApp/tof3/qt_display/qt_display
/myApp/tof3/qt_display/qt_display /tmp/received.dat >> /var/log/tof_display.log 2>&1 &
```

### 6. 验证

观察 `/var/log/tof_display.log`（或串口实时输出）：

- 应看到：`qt_display: fullscreen requested after show`
- weston 应回应 `xdg_toplevel.configure` 带 fullscreen state（而非 `WindowNoState`）
- 无深度帧时屏幕应显示**蓝底**（`QColor(24,72,128)`）+ **中央绿块**（`QColor(0,220,80)`）

## weston.ini transform 调试（颠倒问题）

若屏幕颠倒，通过串口修改 `/etc/xdg/weston/weston.ini`：

```ini
[output]
name=DSI-1
transform=rotate-270   # 原为 rotate-90，若颠倒则改此值
```

修改后重启 weston：

```bash
killall weston; sleep 1; weston &
```

候选值顺序测试：`normal` → `rotate-90` → `rotate-180` → `rotate-270`。

## 注意事项

- `.gitignore` 已忽略 `rk3568/qt_display/qt_display`（编译产物不入库，只提交源码）
- 串口传大文件参考 `deploy/step4_rk_reboot.py` 的 `upload_file()` 函数（base64 分 60 字节块，delay=0.2s）
- SDK 机应使用 Linux 4.19 对应的 Buildroot SDK（v1.0.1，`20230921` 版本）
- 若 S96tof_display 已在开机自启，部署后直接 `reboot` 会比手动 kill + 重起更干净
