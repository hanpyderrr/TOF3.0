# schema — 场景元数据规范

哪吒采集时,**每次采集会话**(operator 触发的一段连续采集)按下面两个 schema 写元数据。
这是后续配对、训练、A/B 评估、模型回滚都依赖的**唯一真相源**。

## 文件

| 文件 | 用途 | 落盘位置(运行时) |
|------|------|-------------------|
| `session_manifest.schema.json` | 一次会话的全局快照(操作员/环境/硬件/雾协议/配对/git_commit) | `~/tof-data/sessions/<session_id>/manifest.json` |
| `frame_record.schema.json`     | 每帧一行 JSON(JSONL),帧级激光/电机/Q/raw 保留决策 | `~/tof-data/sessions/<session_id>/frames.jsonl` |

两个 schema 都遵循 JSON Schema draft 2020-12。

## session_id 命名规范

```
session_id = "<YYYYMMDDTHHMMSS>-<6char_rand>"
e.g.  20260526T143012-a3f9k1
```

`YYYYMMDDTHHMMSS` 为 UTC 起始时间(便于排序);6 字符随机串避免同秒冲突。
正则:`^[0-9]{8}T[0-9]{6}-[a-z0-9]{6}$`(已写进 schema)。

## 会话目录结构

```
~/tof-data/sessions/<session_id>/
├── manifest.json            按 session_manifest.schema.json
├── frames.jsonl             按 frame_record.schema.json(每行一对象)
├── depth/                   .tofrec 文件,frame_record.depth_path 引用此目录
│   ├── 000001.tofrec
│   └── ...
└── raw/                     仅事件触发保留的 .tch,frame_record.raw_path 引用
    ├── 000123.tch
    └── ...
```

## 验证

任意 JSON 工具都能用,例如 Python:

```python
import json, jsonschema

with open("ml_offline/schema/session_manifest.schema.json") as f:
    schema = json.load(f)
with open("~/tof-data/sessions/20260526T143012-a3f9k1/manifest.json") as f:
    inst = json.load(f)

jsonschema.validate(inst, schema)   # 抛 ValidationError 即不合规
```

CI/采集端建议:**写入前在内存验证一次,不合规拒绝写盘**。否则后期数据集会有静默坏样本。

## 关键字段约定

- **`environment.scene_type`**:`calibration_target` / `static_scene` / `moving_scene` / `fog_chamber` / `free_field` —— 决定后续训练时这条 session 进哪个数据池。
- **`fog`** (会话级):`null` = 清空气;非 null 时 `level` ∈ {clear, light, medium, dense}。是否在 `fog_chamber` 室内由 `environment.scene_type` 决定,不在这里。
- **`pair_with`**:这是**(清空气, 雾天) 自动配对**的关键。雾天 session 在这里填同视角同物体的清空气 session_id;训练管道靠它构造 (input=foggy, target=clear) 对。同一 session 内不能"自配对"。
- **`hardware.pf32_mode`**:默认 `sys_master`(项目锁定决策,见 `CLAUDE.md`),只有故意做 laser_master 实验才填别的。
- **`git_commit`**:采集时 TOF3.0 仓库 HEAD,便于复现"用当时代码产出这批数据时的算法版本"。
- **`frame_record.raw_kept_reason`**:`null` = 这帧 raw 没存(常规节流);否则记保留触发原因,事后追责/筛选用。
- **`frame_record.quality`**:Level 0 物理算法输出的 Q 四元组——既是闭环 reward 也是 raw 保留触发依据,要全链路一致。

## 字段填充方式

按"谁填"分三类。**目标:操作员负担最低,绝大多数字段自动推断**。

| 类型 | 字段 | 来源 / 时机 |
|------|------|-------------|
| **自动 (进程读硬件/系统)** | `session_id`, `start_time`, `host.*`, `git_commit`, `hardware.{laser_model, pf32_mode, extstop_delay_ticks}`,以及 `frame_record` 的 `t`, `seq`, `laser.{level, pulse_width_ns, trigger_mode}`, `motor.{focus_step}`, `quality`, `valid_count`, `raw_kept_reason` | 启动会话/每帧实时 |
| **CLI (会话启动一次性)** | `operator` (默认 `$USER`), `environment.{location, scene_type, ambient_lux}`, `fog.*`, `calibration_target.*`, `pair_with` | 操作员调用 `start_session.sh` 时给参数 |
| **运行时人工标 (可选)** | `notes`, `frame_record.tag` | 操作员把字符串 echo 到 trigger 文件,采集进程异步合并 |

### 会话启动脚本(计划中,Phase A 末尾)

```bash
# nezha/acquisition/start_session.sh (planned)
./start_session.sh \
  --location lab \
  --scene fog_chamber \
  --fog medium --visibility 5 \
  --pair-with 20260520T143012-a3f9k1     # 配对清空气 session,可选
```

脚本职责:
1. 生成 `session_id`,创建 `~/tof-data/sessions/<session_id>/` 目录骨架
2. 合并 自动推断字段 + CLI 字段 → `manifest.json`,**写盘前用 schema 验证**
3. 启动 `acquisition` 进程(注入 session_id),监听 `~/tof-data/.tag_queue` 异步合并 tag
4. 监听 SIGINT 优雅退出 → 回写 `end_time`

### 自动推断的字段来源

| 字段 | 来源 |
|------|------|
| `session_id`        | `time.strftime("%Y%m%dT%H%M%S") + "-" + secrets.token_hex(3)` |
| `start_time`        | `datetime.now(timezone.utc).isoformat()` |
| `host.hostname/ip`  | `socket.gethostname()` / `socket.gethostbyname(hostname)` |
| `git_commit`        | `git -C /home/ding/tof3-rt rev-parse HEAD` (失败时 null) |
| `hardware.pf32_mode` | 配置常量 `sys_master`(锁定决策) |
| `hardware.extstop_delay_ticks` | `PF32 API getEXTSTOPDelay()` (PF32 到位后) |
| `frame.laser.*`     | `LaserUart::currentLevel/m_extTrigger/...`(代码已有状态) |
| `frame.quality`     | Level 0 物理算法实时输出 |
| `frame.raw_kept_reason` | `policy/event_trigger.yaml` 规则判定 |

## 演进策略

- 新增字段:加在 schema 末尾,默认值或 nullable,**不破坏旧数据**。
- 删字段:**不删**,改成 `deprecated: true` 注释保留,直到旧数据全归档。
- Schema 版本号通过 `$id` URL 里的版本段管理(未来若有破坏性变更)。
