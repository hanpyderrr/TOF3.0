# cloud_syncer 代码计划（RK3568 5G 上传云端）

> 版本：2026-05-19　状态：计划（待确认决策后实现）
> 关联：`docs/rk3568_framework.md` §3.2、`cloud/server/main.py`、`nezha/qt_app/cloudsyncer.{h,cpp}`

---

## 1. 范围与前提

**职责**：RK3568 上的常驻进程，扫描 `~/tof-buffer/` 中 spi_receiver 重组完成的文件，
5G 在线时 POST 到云端 FastAPI，成功后删本地文件并把上传进度暴露给 spi_receiver（经 SPI CMD=0x05 回报哪吒）。

**前提/边界**：
- 语言 Python 3.8（板上自带）；**仅用标准库**（板上无网络，避免 pip 依赖）→ HTTP 用 `urllib.request`，不引入 `requests`
- 输入文件由 spi_receiver 产出，cloud_syncer 不碰 USB-SPI 设备（设备归 spi_receiver 独占）
- 失败绝不阻塞 spi_receiver / 采集；本地暂存 + 重试
- 上传两类文件：`.tof`（深度录制，端点已存在）、`.tch`（TCSPC 2MB，端点 P9-1 待建）

---

## 2. 数据契约

### 2.1 云端端点

| 端点 | 状态 | 契约 |
|------|------|------|
| `GET /api/health` | ✅ | 200 + `{"status":"ok"}` |
| `POST /api/frames/depth` | ✅ | `{session_id, frames:[{seq:int, ts_ms:int, valid_count:int, depths_b64:str}]}`；`depths_b64` 解码须=2048B；返回 `{"accepted":int}` |
| `POST /api/frames/tcspc` | ⬜ P9-1 | 见 §6（含存储方式待定） |

### 2.2 输入文件格式（来自 ~/tof-buffer/）

**`.tof` 深度录制**（与 `nezha/qt_app/datarecorder` 一致）：
```
头 8B   "TOFREC1\0"
每帧 2062B  seq(u32 LE) ts_ms(u64 LE) validCount(u16 LE) depths(1024×u16 LE = 2048B)
```
→ 每帧映射为 depth 端点的一个 frame，`depths_b64 = base64(2048B depths)`。

**`.tch` TCSPC**（见 `ARCHITECTURE.md` §六）：
```
magic 8B "TCHIST1\0" | seq u32 | w/h u16/u16 | bins u16 | sampleBytes u16 |
payloadBytes u64 | payload(32×32×1024×u16 = 2MB)
```

### 2.3 session_id 约定（开放项 O3）

沿用哪吒 CloudSyncer 约定：`session_id = 文件名去扩展名`（`completeBaseName`）。
spi_receiver 落盘路径建议 `~/tof-buffer/<session>/<name>.tof`，cloud_syncer 取 `<name>` 为 session_id。
→ **需哪吒 SpiSyncer / spi_receiver / cloud_syncer 三方命名统一**（待 SpiSyncer 设计时锁定）。

---

## 3. 模块文件结构

```
rk3568/cloud_syncer/
├── README.md              （已存在，指向本计划）
├── cloud_syncer.py        入口：守护循环，组装各组件
├── config.py              配置（环境变量 / 命令行覆盖，不硬编码）
├── buffer_scanner.py      扫描 ~/tof-buffer/，挑选"完整"文件
├── state_db.py            sqlite 上传状态（断点续传 + 幂等）
├── tof_parser.py          .tof / .tch 解析为可上传单元
├── uploader.py            HTTP 客户端（urllib），depth/tcspc 两路
├── net_status.py          读取 net_manager 暴露的在线状态
├── status_writer.py       写 ~/tof-buffer/.upload_status.json（供 spi_receiver 发 CMD=0x05）
└── tests/                 x86 离线单测（解析/状态机/打包，mock HTTP）
```

> net_manager 本身是独立模块（框架 §3.4），cloud_syncer 只通过 `net_status.py` 读其状态，二者解耦。

---

## 4. 组件设计

### 4.1 config.py
- 来源优先级：命令行 > 环境变量 > 默认
- 字段：`buffer_dir`(默认 `~/tof-buffer`)、`cloud_base_url`、`poll_interval_s`(默认 10)、
  `health_interval_s`(默认 30)、`depth_batch`(默认 50，对齐哪吒 kBatchSize)、
  `tcspc_chunk_bytes`、`max_retry`、`state_db_path`、`status_file_path`、`delete_after_upload`(bool)
- 不硬编码 IP/端口/设备名（遵守项目约束）

### 4.2 buffer_scanner.py
- 只挑**完整**文件：约定 spi_receiver 写 `name.tof.part`，重组完成原子 `rename` 为 `name.tof`
- cloud_syncer 只处理无 `.part` 后缀的 `.tof`/`.tch`，按 mtime 升序（FIFO）
- 输出待办列表，交给状态机

### 4.3 state_db.py（关键——幂等与断点续传）
sqlite 表（仿哪吒 `cloudsyncer.cpp` 的 queue 思路）：
```
upload(file_path PK, kind('tof'|'tch'), session_id, total_units, units_sent,
       status('pending'|'uploading'|'done'|'error'), last_error, created_at, updated_at)
```
- `total_units`：.tof=帧数；.tch=1（整文件）或分块数
- 续传：重启后从 `units_sent` 继续，不重发已确认部分
- 幂等依据见 §5

### 4.4 tof_parser.py
- `iter_tof_frames(path, start_frame) -> yield (seq, ts_ms, valid_count, depths_2048b)`
  - 校验头 `TOFREC1\0`；按 2062B 跨步 `seek(8 + i*2062)`；文件尾不足一帧则停
- `read_tch_header(path) -> dict` + 流式读 payload（2MB，避免一次性大内存：分块读/上传）

### 4.5 uploader.py（urllib，stdlib）
- `post_json(url, dict, timeout) -> (status_code, resp_dict)`；连接/超时异常转可重试错误
- `upload_depth_batch(session_id, frames)` → `POST /api/frames/depth`，按返回 `accepted` 推进 `units_sent`
- `upload_tcspc(session_id, header, payload_iter)` → `POST /api/frames/tcspc`（待 §6 定稿）
- 重试：指数退避，超 `max_retry` 标 `error`，下轮再试，不阻塞其他文件

### 4.6 net_status.py
- 读取 net_manager 暴露的在线状态（约定：net_manager 写 `~/tof-buffer/.net_status` 或 `GET /api/health` 自探）
- 阶段一（net_manager 未实现）降级策略：直接 `GET /api/health` 探活代替

### 4.7 status_writer.py
- 上传进度写 `~/tof-buffer/.upload_status.json`：`{online, queue_len, current_file, units_sent, total, last_success_seq, last_error, ts}`
- spi_receiver 在收到哪吒 CMD=0x01(QUERY) 时读此文件，组 CMD=0x05 回包
- **解耦点**：cloud_syncer 不直接发 SPI；SPI 帧由 spi_receiver 负责（设备独占）

### 4.8 cloud_syncer.py（守护主循环）
```
load config → 初始化 state_db → 循环:
  if not online(net_status/health): sleep(health_interval); continue
  scan buffer → 入/更新 state_db
  取最旧 pending/uploading 文件:
    .tof → 逐 batch 上传(从 units_sent 续) → 进度写 state_db + status_file
    .tch → 上传(整/分块) → 同上
  完成: delete_after_upload 则删文件，状态 done
  错误: 记 last_error，继续下一个，不退出
  sleep(poll_interval)
```
- 信号处理 SIGTERM：当前 batch 落状态后干净退出（配合 autostart stop）

---

## 5. 上传状态机与幂等性（待确认决策 D1）

**问题**：云端 `/api/frames/depth` 是裸 `INSERT`，`idx_session(session_id,seq)` **非 UNIQUE** →
重试/重启重发会在云端产生重复帧。

**方案 A（默认推荐，零云端改动）**：RK3568 侧 `state_db` 严格记 `units_sent`，
只在收到云端 `accepted` 后推进；崩溃恢复从 `units_sent` 续传。
风险残留：POST 成功但响应丢失 → 该 batch 可能重复（小概率，可接受/可人工去重）。

**方案 B（更稳，需改云端）**：云端 `frames` 表加 `UNIQUE(session_id, seq)`，
depth 端点改 `INSERT OR IGNORE` / upsert，返回真正新增数。RK3568 侧逻辑简化。

→ 倾向 A（本轮不改云端契约，与哪吒现有 CloudSyncer 行为一致）；B 作为后续加固项。**请确认。**

---

## 6. P9-1 配套：POST /api/frames/tcspc（待确认决策 D2）

cloud_syncer 上传 TCSPC 必须有此端点。TCSPC 单帧 2MB，**存储方式是设计分叉**：

| 方案 | 说明 | 取舍 |
|------|------|------|
| B1 文件系统 | 服务端存 `data/tcspc/<session>/<seq>.tch`，DB 只存元数据+路径 | 推荐：2MB BLOB 不进 SQLite，利于 ML 批读 |
| B2 SQLite BLOB | 与 depth 一致，存 BLOB | 简单但 DB 膨胀快、ML 读取低效 |

建议端点形态（multipart 或 raw body + query/header 元数据，避免 base64 膨胀 33%）：
```
POST /api/frames/tcspc?session_id=&seq=&width=&height=&bins=
Content-Type: application/octet-stream
body = 原始 .tch payload(2MB)
→ 落 data/tcspc/<session>/<seq>.tch + INSERT tcspc_frames(元数据,path)
```
→ 端点实现属 `cloud/server/`，是 cloud_syncer 的前置；建议先做 B1。**请确认 B1/B2。**

---

## 7. 错误处理 / 不阻塞原则

- 任一文件失败：记 `last_error`，跳过继续下一个，进程不退出
- 网络断：暂停上传，文件原地保留，恢复后续传
- 解析失败（坏文件）：移到 `~/tof-buffer/.bad/` 并记日志，不反复卡死
- 磁盘满：日志告警，停止删除/上传，等空间（不崩溃）
- 日志：`/var/log/tof_cloud_syncer.log`，滚动（size 上限），级别可配

---

## 8. 配置项（命令行 / 环境变量，不硬编码）

`--buffer-dir --cloud-url --poll-interval --health-interval --depth-batch
--max-retry --state-db --status-file --no-delete --log-file --log-level`

---

## 9. 分阶段实施与可测试性

| 阶段 | 内容 | 在哪测 | 依赖 |
|------|------|--------|------|
| C1 | tof_parser + state_db + uploader(depth) + 主循环 | x86 本地：起本地 FastAPI + 造 .tof，mock buffer | 无（端点已存在）|
| C2 | buffer_scanner 完整文件判定 + status_writer + 配置/日志 | x86 本地 | C1 |
| C3 | 云端 `POST /api/frames/tcspc`（B1）+ uploader(tcspc) | x86 本地 | D2 确认 |
| C4 | net_status 对接 net_manager + autostart 脚本 | RK3568 | net_manager |
| C5 | 与 spi_receiver 联调（.part→rename、status.json→CMD0x05） | RK3568 | spi_receiver |

> C1–C3 全部可在 x86 开发机离线验证（不需要 RK3568、不需要 5G、不需要 USB-SPI）。
> 单测：`.tof` 解析边界（尾部残帧/坏头）、状态机续传、batch 推进、重试退避。

---

## 10. 待确认决策

| # | 决策 | 选项 | 结论 |
|---|------|------|------|
| D1 | 上传幂等策略 | A: RK3568 状态续传(不改云端) / B: 云端 UNIQUE+upsert | ✅ **A**（已实现，B 留作后续加固） |
| D2 | 云端 TCSPC 存储 | B1: 文件系统+元数据 / B2: SQLite BLOB | ⬜ 待定（本轮不做 TCSPC，倾向 B1） |
| D3 | net_manager 状态接口形态 | 状态文件 / HTTP 自探(health) 降级 | ✅ 当前用 `/api/health` 自探 |
| D4 | 上传成功后是否删本地 | 删 / 保留(配额回收) | ✅ 默认删，`--no-delete` 可关 |
| D5 | session/文件命名约定（O3） | 待与 SpiSyncer/spi_receiver 一起锁 | ⬜ 暂用文件名去扩展名 |

> 实施状态（2026-05-19）：§9 的 **C1+C2 深度上传已实现并通过离线 e2e**
> （3 场景 14 项断言全过：全量上传 / 断网续传无重复 / 坏文件隔离）。
> C3（TCSPC，依赖 D2）、C4（net_manager）、C5（spi_receiver 联调）待后续。

---

## 11. 验收标准

- 本地 FastAPI + 造 100 帧 `.tof`：cloud_syncer 全部上传，`GET /api/sessions` 帧数一致
- 上传中 kill 进程重启：不重复、不丢帧，从断点续传
- 断网→恢复：自动续传，进程全程不退出
- 坏文件：隔离到 `.bad/`，不影响其他文件上传
- 全流程 0 处硬编码 IP/端口/路径（均可配）
