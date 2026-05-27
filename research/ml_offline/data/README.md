# data — 离线数据布局

哪吒采集的 raw + 深度 + 元数据,周期同步到这里(开发机/工作站),供训练/评估使用。
**仓库不存数据**(`.gitignore` 已忽略各子目录的 *.tch/*.tofrec),只入版本控制本 README
与极小的 sample/示例。

## 子目录

| 子目录 | 内容 | 数据量级 |
|--------|------|----------|
| `raw_dump/` | 从哪吒 rsync 下来的 raw .tch + depth .tofrec,按 `<session_id>/` 组织 | 几 GB ~ 几十 GB |
| `meta/`     | 各 session 的 `manifest.json` + `frames.jsonl`(同步自哪吒) | MB 量级 |
| `labels/`   | 自动生成的弱监督标签(物理算法跑出的 depth/Q,长曝光累加 pseudo-GT) | 与 raw 量级相当 |
| `tof_dataset.py` | PyTorch `Dataset`:读 .tch + 对应 label,做 (input, target) 配对 | — |

## 同步入口

`deploy/sync_raw.py` (Phase B 添加) 做:
- SSH/SFTP 连哪吒
- `rsync` 增量拉 `~/tof-data/sessions/` 到本机 `data/raw_dump/` 与 `data/meta/`
- 校验 manifest schema 合规
- 可选:同步后哪吒侧按保留策略删除老 session(磁盘空间管理)

## 标签生成

`labels/` 不入版本控制,由本地脚本(Phase A 末尾添加)生成:

```bash
python ml_offline/train/build_labels.py \
  --session-meta data/meta/<session_id>/manifest.json \
  --source long_exposure_64x \
  --out data/labels/<session_id>/
```

候选 source:
- `long_exposure_64x` — 64 帧累加当 pseudo-GT(雾分离 self-supervised 主路径)
- `level0_physical` — Level 0 物理算法输出当软标签
- `clear_pair`      — 通过 `manifest.pair_with` 找清空气对应帧,做雾→清直接监督
- `calib_target`    — 标定靶板的真距(高精度小数据,验证集用)

## 数据集索引

`tof_dataset.py` 构造时按 `meta/` 索引,过滤 `environment.scene_type` 选场景,按
`fog.level` 分桶。**不在文件名里编码场景信息**,全部由 manifest 驱动——这样数据
重新打标只改 manifest,不动文件。
