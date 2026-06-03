# refs/pf32/docs — PF32 文档索引

每个 PDF 读取后在同目录建同名 `.md` 提取关键信息，此处为一行简介索引。

| 文件 | 简介 | 笔记 |
|------|------|------|
| `PF32 Manual.pdf` | PF32 SPAD 探测器完整用户手册（硬件、固件、API、操作说明） | 未读 |
| `PF32 Manual的全文翻译.pdf` | 上述手册中文全文翻译 | ✅ 已读，见同名 `.md` |
| `PF32 Quick Start Guide.pdf` | PF32 快速上手指南（连接、固件加载、首次采集） | 未读 |
| `PF32 Quick Start Guide的全文翻译.pdf` | 上述快速指南中文全文翻译 | 未读 |
| `pf32API.pdf` | PF32 C/C++ & Python API 参考（函数签名、TCSPC 模式、数据格式） | 未读 |
| `pf32API的全文翻译.pdf` | 上述 API 手册中文全文翻译 | 未读 |
| `PF_Matlab_Wrapper.pdf` | PF32 MATLAB 封装 API 参考 | 未读 |
| `PF_Matlab_Wrapper的全文翻译.pdf` | 上述 MATLAB 封装中文全文翻译 | 未读 |
| `SyncInput_3300mV.pdf` | PF32 SYNC 输入电气规格（3.3V 上限），适用于 laser_master 接法（**本项目不使用**，见注） | 未读 |
| `SyncInput_3300mV的全文翻译.pdf` | 上述 SYNC 输入规格中文翻译 | 未读 |

> **本项目 TCSPC 模式**：`TCSPC_sys_master`（PF32 做主，出 TRIG 触发激光，内部 EXTSTOP 做 stop）。
> `SyncInput_3300mV.pdf` 描述的是 laser_master 反向接法（激光 SYNC → PF32 SYNC 输入），**不适用本项目**，勿据此接 PF32 SYNC 口。
> 权威实现：`refs/pf32/samples/PhotonForce/C++/FW_Histogramming.cpp`、`ExampleTOF.cpp`（全部用 `TCSPC_sys_master`）。
