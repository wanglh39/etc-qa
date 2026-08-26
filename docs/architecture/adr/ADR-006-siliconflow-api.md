# ADR-006: Embedding/Reranker 改用 SiliconFlow API 替代本地模型

**状态**：已接受  
**日期**：2026-08-25

## 背景

原方案使用本地 SentenceTransformer（bge-large-zh-v1.5）和 CrossEncoder（bge-reranker-large）模型，存在以下问题：

1. **模型体积大**：bge-large-zh-v1.5 (~1.3GB) + bge-reranker-large (~2.2GB) = ~3.5GB，下载慢、占磁盘
2. **依赖重**：sentence-transformers + torch + transformers，安装慢、Docker 镜像大
3. **GPU 依赖**：CPU 推理慢（Reranker 单次 ~200ms），GPU 部署门槛高
4. **多实例浪费**：每个后端实例都加载一份模型，显存/内存重复占用

## 决策

将 Embedding 和 Reranker 改为 **SiliconFlow API** 调用，并实现多 key 负载均衡。

- Embedding：bge-large-zh-v1.5（1024 维，与原模型一致）
- Reranker：bge-reranker-v2-m3（比原 bge-reranker-large 更新，多语言支持）
- 客户端：`rag/siliconflow.py`，EmbeddingClient/RerankClient 作为原接口替身
- 负载均衡：最长空闲优先选 key，429/5xx 自动冷却 60s 切下一个

## 理由

1. **零本地依赖**：移除 sentence-transformers + torch，Docker 镜像减小 ~2GB
2. **弹性扩缩**：API 按量付费，无需预估 GPU 数量；多实例共享 API 配额
3. **多 key 容错**：SiliconFlow 免费 key 有 QPS 限制，多 key 负载均衡突破单 key 限流
4. **模型升级**：bge-reranker-v2-m3 比原模型更新，精度更高
5. **接口兼容**：EmbeddingClient.encode() / RerankClient.predict() 与原接口一致，调用方零改动

## 代价

- 网络延迟：API 调用增加 ~50-100ms（本地 GPU ~10ms），但 RAG 总链路可接受
- 依赖外部服务：SiliconFlow 宕机则 RAG 不可用（多 key 冷却机制缓解单 key 故障）
- 阈值重调：bge-reranker-v2-m3 分数尺度与 bge-reranker-large 不同，已重调 rag.yaml 阈值

## 参考

- [SiliconFlow API 文档](https://docs.siliconflow.cn)
- rag/siliconflow.py 实现代码
- config/models.yaml API 配置

---

> 注：本ADR仅涉及Embedding/Reranker。ASR改用阿里云NLS API的决策见ADR-007。