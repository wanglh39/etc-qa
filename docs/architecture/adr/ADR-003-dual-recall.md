# ADR-003: 双路并行召回（Milvus + BM25）而非单路向量检索

**状态**：已接受  
**日期**：2026-07-15

## 背景

RAG 检索需要从知识库中找到最匹配的 QA。候选方案：

1. **纯向量检索** — Milvus 语义匹配
2. **纯 BM25** — 关键词匹配
3. **双路并行召回 + RRF 合并** — 向量 + BM25 并行，倒数排名合并

## 决策

选择 **双路并行召回 + RRF 合并**。

## 理由

1. **互补**：向量检索擅长语义匹配（"怎么换手机号" ≈ "如何变更绑定号码"），BM25 擅长关键词匹配（ETC、OBU 等专有名词）
2. **并行**：ThreadPoolExecutor(max_workers=2) 并行执行，延迟不增加
3. **RRF 权重**：vector_weight=0.7, bm25_weight=0.3，向量为主、BM25 补充
4. **Reranker 精排**：合并后用 CrossEncoder 精排，提升 Top-1 准确率

## 代价

- 资源消耗增加（同时维护 Milvus + BM25 索引）
- BM25 索引需随数据更新重建（已通过线程安全 RLock 解决）

## 参考

- [RRF 论文](https://plg.uwaterloo.ca/~gvcormac/cormacksigir12-rrf.pdf)