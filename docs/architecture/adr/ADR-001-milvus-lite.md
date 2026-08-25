# ADR-001: 选择 Milvus Lite 而非 Pinecone/Weaviate

**状态**：已接受  
**日期**：2026-07-01

## 背景

项目需要向量数据库存储 QA 问题向量（1024 维），支持语义检索。候选方案：

1. **Milvus Lite** — 本地文件，无需独立部署
2. **Pinecone** — 云托管 SaaS
3. **Weaviate** — 开源，需独立部署

## 决策

选择 **Milvus Lite**。

## 理由

1. **零运维**：本地 SQLite 文件，无需独立部署 Docker 容器，适合挑战杯演示环境
2. **成本**：免费开源，Pinecone 按用量收费
3. **性能**：本地文件 IO 比网络调用快，延迟 < 10ms
4. **迁移**：如需升级到分布式 Milvus 集群，API 兼容，代码零改动
5. **隐私**：数据不出本地，Pinecone 需上传到云端

## 代价

- 不支持分布式（单机限制，但项目数据量 < 10万条，足够）
- 并发写入有限（已通过 RLock 解决线程安全）

## 参考

- [Milvus Lite 文档](https://milvus.io/docs/milvus_lite.md)