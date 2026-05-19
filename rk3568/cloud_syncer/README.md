# cloud_syncer — 5G 上传到云端 FastAPI

> ⏸️ **本阶段暂缓**（2026-05-19 决策）：5G 上云日后稳定再加。
> 本模块**已完整实现并通过离线 e2e，代码保留不动**；待 P-5G 阶段接真实云平台 + 5G。
> 本阶段链路只做"哪吒实时深度 → SPI → RK3568 Qt MIPI 显示"，不经本模块。

完整设计见 [`docs/rk3568_framework.md`](../../docs/rk3568_framework.md) §3.4。
代码实施计划见 [`docs/cloud_syncer_plan.md`](../../docs/cloud_syncer_plan.md)。

## 职责

轮询 `~/tof-buffer/` 下 spi_receiver 重组完成的文件，5G 在线时 POST 到云端 FastAPI，
成功后删本地文件，并经 SPI CMD=0x05 回报进度给哪吒。

## 决策（已锁定）

- 语言：**Python 3.8，仅标准库**（板上无网络，不引入 pip 依赖；HTTP 用 urllib）
- D1=**A**：本地 sqlite 状态库断点续传，不改云端契约（裸 INSERT）
- 本轮**只做深度 `.tof` 上传**（端点已存在）；TCSPC 端点+上传后续单独做
- 上传前 `GET /api/health` 自探；net_manager 后续接入
- 失败不阻塞、不退出，重试 + 本地暂存；进度写状态文件供 spi_receiver 发 CMD=0x05

## 状态

✅ 深度上传已实现并通过离线 e2e（3 场景 14 项断言全过）

## 模块

`config.py` `state_db.py` `tof_parser.py` `uploader.py` `buffer_scanner.py`
`status_writer.py` `cloud_syncer.py`(入口) + `tests/`

## 运行

```bash
python3 cloud_syncer.py --cloud-url http://<云端>:8765 \
    --buffer-dir ~/tof-buffer
# 其余参数见 --help（poll/health 间隔、batch、重试、状态库/文件路径、--no-delete）
# 环境变量等价覆盖：TOF_CS_CLOUD_URL 等
```

## 测试（离线，无需 RK3568/5G/FastAPI）

```bash
python3 tests/test_e2e.py   # 退出码 0=全过
```

场景：① 137 帧全量上传 ② 断网中断后续传（无重复/不丢帧）③ 坏文件隔离。

## 剩余缺口

- TCSPC：云端 `POST /api/frames/tcspc` 与对应上传（D2 待定 B1/B2，本轮不做）
- net_manager 未接入（当前用 `/api/health` 自探代替）
- autostart 脚本（待与 spi_receiver 一起落地）
- 5G 未插 SIM → 无网前只能本地暂存（框架文档 §6 O5）
- 与 spi_receiver 的 `.part→rename` 落盘约定、status.json→CMD0x05 需联调
