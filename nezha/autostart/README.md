# 哪吒侧开机自启（systemd）

室外生产时哪吒**无网无人值守**，采集 + SPI 推送链路必须开机自启、崩溃自愈。

## 链路

```
tof-acquisition.service  → sim_pf32 → /tmp/depth.dat
tof-spi-syncer.service   → spi_syncer(root) → /dev/spidev1.0 → RK3568
```

- `spidev1.0` 由 BIOS ACPI(`SSDT SPIDEV1`)+spidev 模块**开机自动出现**(~2.5s)，无需手动加载。
- `tof-spi-syncer` 用 `ExecStartPre` 等 `spidev1.0` + `depth.dat` 就绪(最多 60s)，`Restart=always` 兜底。
- 当前 acquisition 跑 **sim_pf32 模拟器**；接真实 PF32 后改 `tof-acquisition.service` 的 `ExecStart` 为真实采集程序。

## 安装（哪吒上，需 root）

```bash
sudo cp tof-acquisition.service tof-spi-syncer.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable tof-acquisition tof-spi-syncer
sudo systemctl start  tof-acquisition tof-spi-syncer
```

## 禁用旧 v1.0 自启（必须，否则抢 /dev/spidev1.0）

旧单光子 v1.0 在用户 crontab 有 `@reboot ... PF32dataAcquisitionAndSPIsend.sh`（文本协议 spisendfile），与 TOF3.0 冲突：

```bash
crontab -l > ~/crontab.bak.$(date +%s)              # 备份
crontab -l | sed '/PF32dataAcquisitionAndSPIsend/s/^/#/' | crontab -   # 注释掉
```

## 验证

```bash
systemctl status tof-acquisition tof-spi-syncer --no-pager
# depth.dat 在涨：
python3 -c "import struct;d=open('/tmp/depth.dat','rb').read();print(struct.unpack('<I',d[8:12])[0])"
# RK3568 串口看 /var/log/tof_display.log 的 read frame seq 递增
```

## 日志

```bash
journalctl -u tof-acquisition -u tof-spi-syncer -f
```
