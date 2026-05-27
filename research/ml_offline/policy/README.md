# policy — 运行策略(数据驱动可调参数)

这里的 YAML **不是代码**,运行时由 acquisition / shadow_mode / event_trigger 加载。
后期标定后可独立调,不需要改代码或重启服务(若实现热重载)。

## 文件

| 文件 | 用途 | 当前状态 |
|------|------|----------|
| `event_trigger.yaml` | raw 保留触发(Q σ 阈值、定时采样、手动入口、磁盘保护) | 起步值,真实数据回来后标定 |
| `shadow_mode.yaml`   | 新 ONNX 上线影子模式(对比期、判定指标、回滚阈值) | 起步值,首次上线观察后调 |

## 起步值约定

- 所有阈值都标注 `# starter, tune after ...`,**真实数据/模型回来后再调**
- 改动时**保留旧值在注释里**(`# 2026-05-26 was: 100, raised to 200 after ...`),
  便于回滚和 A/B 调参溯源
- 重大调整(>2× 偏离 starter)建议同时在 `docs/agent-work/progress.md` 记一条

## 加载方

| YAML | 加载者 | 加载时机 |
|------|--------|----------|
| `event_trigger.yaml` | `nezha/acquisition/raw_recorder`(待写) | 进程启动 + 收到 SIGHUP 时热重载 |
| `shadow_mode.yaml`   | `ml_offline/eval/shadow_mode.py` + `nezha/ml_runtime`(待写) | 模型部署前由 eval 读取;线上由 ml_runtime 读 |
