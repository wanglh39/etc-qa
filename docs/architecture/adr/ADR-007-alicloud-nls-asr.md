# ADR-007: ASR 改用阿里云 NLS API 替代本地模型

**日期**: 2026-08-26
**状态**: 已接受

## 背景

初版ASR采用本地模型方案：
- FunASR（Fun-ASR-Nano-2512）作为基座模型
- silero-vad（torch）做静音切句
- pyannote做说话人分离
- 模型文件约2.1GB，需下载到本地
- 依赖torch/pyannote/funasr，安装复杂（需CUDA）
- Windows多线程环境下FunASR会crash，需subprocess隔离

## 决策

ASR改用阿里云NLS（自然语言交互）API：
- 阿里云NLS实时语音识别API（WebSocket协议）
- 热词表在NLS控制台配置（ETC/OBU/蓝牙等22个领域专有名词）
- Token通过aliyunsdkcore自动获取+缓存
- 保留纠错表（字符串替换，config/asr.yaml）
- 移除torch/pyannote/funasr依赖，改用aliyunsdkcore+websocket-client

## 理由

1. **降低部署成本**：无需GPU服务器，无需下载2.1GB模型文件
2. **简化依赖**：移除torch/pyannote/funasr，避免CUDA/C++ Build Tools安装问题
3. **提升稳定性**：无本地模型加载，无Windows多线程crash问题
4. **识别精度**：阿里云NLS+热词表在ETC领域专有名词识别效果良好
5. **与ADR-006对称**：Embedding/Reranker走SiliconFlow API，ASR走阿里云NLS API，全栈API化

## 影响

- 新增依赖：aliyunsdkcore>=1.0.3, websocket-client>=1.8.0
- 新增配置：ALICLOUD_ASR_APP_KEY/ACCESS_KEY_ID/ACCESS_KEY_SECRET/HOTWORDS_ID
- 代码变更：asr/streaming.py新增AliCloudStreamingBackend
- 移除依赖：funasr/torch/pyannote/modelscope（后续清理）
- 移除文件：asr/diarizer.py, asr/preprocess.py, asr/finetune/
- 文档同步：21个文档已更新