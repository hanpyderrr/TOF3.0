# raw_dump — 哪吒原始数据本地镜像

从哪吒 `~/tof-data/sessions/` 同步下来的 raw .tch + depth .tofrec,按 session 组织:

```
raw_dump/
└── <session_id>/
    ├── depth/
    │   ├── 000001.tofrec
    │   └── ...
    └── raw/
        ├── 000123.tch       # 仅事件触发保留的帧
        └── ...
```

**会话级元数据(manifest + frames.jsonl)放在 `../meta/<session_id>/`**,跟 raw/depth 分开,
便于只同步元数据做轻量索引。

仓库不追踪本目录下数据文件,只追踪本 README。
