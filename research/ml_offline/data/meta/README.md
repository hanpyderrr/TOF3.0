# meta — 各 session 的元数据镜像

每个 session 一个目录:

```
meta/
└── <session_id>/
    ├── manifest.json     符合 ../schema/session_manifest.schema.json
    └── frames.jsonl      每行一对象,符合 ../schema/frame_record.schema.json
```

manifest 是会话级一次写,frames.jsonl 是追加写(append-only,采集时每帧追加一行)。

**同步策略建议**:`meta/` 量小(MB 级),每次都全量 rsync;`raw_dump/` 按需选择性 rsync。
这样开发机即使没拉 raw 也能用 manifest 做数据集索引/筛选/统计。
