# ml_offline — 离线训练 + 边缘推理

TOF3.0 ML 管道。**不上云**:训练数据靠开发期人工同步,训练在工作站/本机 GPU 跑,
模型 ONNX 导出后部署回边缘(默认哪吒 N97 CPU,见 §部署目标)。

> 之前命名 `cloud/ml/`,因 5G 上云方案暂缓 + 转向边缘推理已重命名。
> 历史决策见 `docs/agent-work/progress.md` 2026-05-25。

## 数据 / 模型生命周期

```
[运行时 哪吒]                       [离线 开发机/工作站]                [部署 哪吒]
acquisition → 深度+Q+元数据 (常驻)                                      ┌─────────┐
              raw .tch (事件触发)  ── 周期 rsync ──► raw_dump/         │ ONNX    │
              session manifest                      ──► train/  ──►   │ Runtime │
                                                    ──► export ──►    │ CPU     │
                                                    ──► eval/ A/B    └─────────┘
                                                                          ▲
                                                       新模型 SCP ────────┘
```

## 目录布局

```
ml_offline/
├── schema/                  JSON Schema (session manifest / frame record)
├── data/
│   ├── raw_dump/            从哪吒同步下来的 raw/depth (按 session)
│   ├── meta/                各 session 的 manifest + frames.jsonl
│   ├── labels/              自动生成的弱监督标签(物理算法输出 / 累加帧 GT)
│   └── tof_dataset.py       PyTorch Dataset 加载器(读 .tch + label)
├── models/hist3d_net.py     Hist3DNet (B,1,32,32,1024) + DepthUNet baseline
├── train/train.py           PyTorch 训练 (AdamW + L1+SSIM + cosine LR)
├── export/to_onnx.py        checkpoint → ONNX opset 17 + ORT 校验
├── infer/run_infer.py       开发期 CPU 推理(单文件冒烟用;线上推理在 nezha/ml_runtime)
├── eval/                    A/B 评测 + 影子模式占位
└── tests/                   脚手架自检
```

## 数据契约(.tch TCSPC 直方图)

```text
Header:
  magic        8B  "TCHIST1\0"
  seq          4B  uint32
  width        2B  uint16, 32
  height       2B  uint16, 32
  bins         2B  uint16, 1024
  sampleBytes  2B  uint16, 2
  payloadBytes 8B  uint64
Payload:
  uint16[H*W*BINS]  →  (32, 32, 1024)
```

反向 start-stop:`depth_mm = (1023 - peak_bin) * 55ps * c/2 ≈ (1023 - bin) * 8.243mm`。
归一化:逐样本 `hist / max(hist)`。

## 训练数据来源(标签策略)

按"立刻可用"到"精度最高"排:

| 标签源 | 难度 | 用法 |
|--------|------|------|
| (d) **长曝光累加帧当 GT** (自监督) | 低 | 64 帧累加 SNR×8 当 pseudo-GT,单帧当输入。**Phase A 主数据源** |
| (a) **Level 0-2 物理算法输出** (弱监督) | 低 | algorithm 跑出深度+Q 当软标签 |
| (b) **同场景 (清空气, 雾天) 配对** | 中 | 清空气帧当 GT,通过 manifest 的 `pair_with` 字段配对 |
| (c) **标定靶板** (强 GT) | 中 | 小规模高精度,验证集主力 |

Phase A 用 tof_sim(升级版含 pile-up/Gamma/Skewed)+ Middlebury 深度图当输入预训练;
Phase B 真实 PF32 到位后用 (d)+(a) 主力,(b) fine-tune,(c) 评估。

## 训练 / 导出 / 推理(沿用旧脚手架)

```bash
# 依赖
pip install -r ml_offline/requirements.txt

# 训练(3D 直方图)
python ml_offline/train/train.py \
  --model hist3d \
  --data-dir ml_offline/data/raw_dump/<session>/foggy \
  --clear-dir ml_offline/data/raw_dump/<session>/clear \
  --epochs 20 --lr 0.001 --batch-size 2 \
  --output-dir ml_offline/runs/hist3d --device cuda

# 导出 ONNX
python ml_offline/export/to_onnx.py \
  --model hist3d \
  --checkpoint ml_offline/runs/hist3d/best_model.pth \
  --output ml_offline/runs/hist3d/best_model.onnx

# 单文件冒烟(开发机)
python ml_offline/infer/run_infer.py \
  --model-path ml_offline/runs/hist3d/best_model.onnx \
  --input-tch ml_offline/data/raw_dump/<session>/raw/000001.tch \
  --output-npy /tmp/depth_000001.npy
```

## 部署目标

**默认:哪吒 N97 (x86_64)**,通过 `nezha/ml_runtime/` (待建) 加载 ONNX,ONNX Runtime CPU,
INT8 量化,目标 <50ms/帧(详见 `docs/agent-work/progress.md` 算法时延分档)。

**可选:RK3568 NPU (aarch64, 0.8 TOPS INT8)**——需经 RKNN Toolkit 转换,工具链成本高。
留作显示侧轻量增强(深度图 SR 渲染)的备用,**不在主算法路径**。

## Schema

场景元数据严格按 `schema/` 下两个 JSON Schema:
- `session_manifest.schema.json` — 每次采集会话一份
- `frame_record.schema.json` — JSONL,每帧一行

详见 `schema/README.md`。

## 元数据填充策略

manifest 与 frame_record **大部分字段自动推断**(进程读硬件/系统),操作员只在
会话启动时给极少 CLI 参数(`--location --scene --fog --pair-with`)。详见
`schema/README.md` §字段填充方式。

## 训练资源

**TBD**——训练机器待定。候选:
- 自建 GPU 工作站(RTX/RX)
- 临时租云(autodl/runpod 按小时)
- 本机 CPU 退化模式(小 U-Net,仅冒烟,不出生产模型)

`train/train.py` 支持 `--device cuda|cpu`,资源到位后无需改代码。

## 上线策略 — 影子模式

新 ONNX **不直接 hot-swap**:

1. 离线 A/B 通过(`eval/ab_test.py`)
2. 部署到哪吒,**与 v_current 并行影子跑 N 天**(默认 7 天,见 `policy/shadow_mode.yaml`),
   双模型同时推理,**只比指标,不切主路**
3. v_next 实时 Q 不低于 v_current 设定百分位 → 切主路
4. 异常自动回滚(规则在 `policy/shadow_mode.yaml`)

详见 `eval/README.md` + `policy/shadow_mode.yaml`。

## 运行策略 (`policy/`)

数据驱动可调参数,不入代码:

| 文件 | 用途 |
|------|------|
| `policy/event_trigger.yaml` | raw 保留触发(Q σ 阈值、定时采样、手动入口、磁盘保护) |
| `policy/shadow_mode.yaml`   | 新模型上线观察期 + 回滚阈值 |

**当前值都是起步值**,真实数据/模型回来后再标定。改动时**保留旧值在注释里**,
便于 A/B 调参与回滚。
