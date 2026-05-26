# labels — 自动生成的弱监督标签

不是手标的——是离线脚本基于 raw_dump + meta **自动生成**的训练标签。
本目录不入版本控制,由 `train/build_labels.py` (Phase A 末尾添加) 生成。

## 标签来源

| source | 说明 | 数据形式 |
|--------|------|----------|
| `long_exposure_64x` | 64 帧累加 → 高 SNR depth/hist 当 pseudo-GT,单帧当输入。**Phase A 主数据源**(自监督,数据成本最低) | .npy 深度图 + .npy 直方图 |
| `level0_physical`   | Level 0 物理算法(Gamma+DBSCAN+Skewed Gaussian)输出当软标签 | .npy 深度图 + Q 四元组 .json |
| `clear_pair`        | 通过 `manifest.pair_with` 找清空气帧对当 GT(强监督,但要求场景静态同视角) | .npy 深度图,索引在 .csv |
| `calib_target`      | 标定靶板真距(高精度,小数据量,验证集用) | .csv 索引 |

## 目录布局

```
labels/
└── <session_id>/
    └── <source>/        # e.g. long_exposure_64x/
        ├── 000001.npy   # 深度图 (32,32) float32 mm
        ├── 000001.json  # 附加信息 (Q, source-specific meta)
        └── ...
```

文件名通常与对应 `raw_dump/<session_id>/depth/` 或 `raw/` 的 seq 一致,便于 `Dataset` 配对。
