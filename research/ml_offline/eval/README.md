# eval — A/B 评测与影子模式

新模型部署前的验证关卡。

## 内容(占位,Phase B/C 实现)

| 脚本 | 作用 |
|------|------|
| `ab_test.py`     | 离线 A/B:在 hold-out 数据集上比较两个模型的深度 RMSE、命中率、Q 分布 |
| `shadow_mode.py` | 在线影子模式封装:新旧模型在哪吒并行推理,**只比指标不切主路**,运行 N 天后产报告 |
| `metrics.py`     | 共享指标实现(RMSE、命中率、SBR、Q 直方图差异等) |

## 上线判定建议

新模型替换现役 (`v_current → v_next`) 必须满足:

1. **离线 A/B 通过**:`ab_test.py` 在 hold-out 集上 RMSE 不降、命中率不降、Q 均值不降。
2. **影子模式通过**:`shadow_mode.py` 跑 N 天(N≥7),线上数据上 v_next 的实时 Q 不低于 v_current 的某个百分位(例如 P25)。
3. **回滚预案就绪**:旧模型 ONNX 保留在 `nezha/ml_runtime/models/v_current.onnx`,
   遇到指标异常一条命令切回。

## 模型版本号

语义版本 `MAJOR.MINOR.PATCH`:
- MAJOR:输入/输出契约变化(如 input shape/通道改了)
- MINOR:训练数据集变化但契约不变
- PATCH:同数据再训(种子/超参微调)

ONNX 文件命名:`hist3d_v1.2.0.onnx`,同时在 `eval/runs/<version>/` 保存训练日志、数据集快照 hash、A/B 报告。
