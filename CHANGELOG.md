# 变更日志

本项目所有重要变更记录于此。格式遵循 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.0.0/)，版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

---

## [未发布]

### 新增
- 文档目录重组：按企业级标准分类（architecture/api/database/guides/ops/security/standards/testing/tutorials）
- CHANGELOG.md 变更日志
- CONTRIBUTING.md 贡献指南
- docs/security/安全设计文档.md（RBAC + JWT + 模拟登录 + 数据安全）
- docs/ops/运维手册.md（Runbook + 故障处理 + 告警规则 + 监控指标）
- docs/architecture/adr/ 架构决策记录（ADR-001~006）
- ADR-006: Embedding/Reranker 改用 SiliconFlow API 替代本地模型

### 变更
- **嵌入/重排模型改 SiliconFlow API**：移除 sentence-transformers 依赖，新增 rag/siliconflow.py 多 key 负载均衡
- Reranker 模型从 bge-reranker-large 升级为 bge-reranker-v2-m3，阈值重调适配新分数尺度
- README.md 重写：52 个 API 端点 + 5 角色 RBAC + 测试/CI 描述
- API接口文档.md 重写：全部 52 端点 + JWT 认证 + 5 角色权限 + 状态码
- 数据库设计文档.md 重写：12 表 + Milvus 集合 + 关系图
- 开发规范.md 补充：状态码 401/403/404/429 + 角色权限规范 + 测试/CI 规范
- 开发环境搭建.md 补充：前端启动 + 角色账号 + SiliconFlow API 配置
- 全部文档同步更新 SiliconFlow API 变更（技术栈/部署/运维/交接清单等）

### 移除
- 删除影子测试（shadow_recorder）相关文档引用
- 删除提示词版本管理（version_manager）相关文档引用
- 移除 sentence-transformers + torch 本地模型依赖（Embedding/Reranker 改用 API）

---

## [1.3.0] - 2026-08-24

### 新增
- E2E 测试（Playwright）：3 个 spec，8 个用例（登录/路由守卫/404）
- 前后端契约测试：OpenAPI schema + 3 个契约校验
- 性能测试：pytest-benchmark（JWT 34k ops/s + 密码哈希 16 ops/s + 限流 120k ops/s）
- locust 压测脚本：5 个任务（health/stats/qa/query/categories）
- CI pipeline 升级为 9 个 job

### 变更
- 前端测试体系：57→58 文件，678→681 用例，覆盖率 ≥80%
- prettier 格式化 113 个文件

---

## [1.2.0] - 2026-08-23

### 新增
- 前端测试体系（57 文件/678 用例/覆盖率 ≥80%）
- 统一 CI pipeline（etc_qa/.github/workflows/ci.yml）
- 前端代码质量门禁：ESLint + Prettier + Husky + lint-staged
- vitest.config.ts 覆盖率门槛 80%

### 变更
- 删除 backend/tests/prompt/（已废弃的提示词版本管理测试）
- 删除 backend/.github/（旧 CI 位置错误）

---

## [1.1.0] - 2026-08-22

### 新增
- 后端并发安全改造：加锁 + 超时 + TTLCache + 限流
- Milvus 连接线程安全（RLock）
- 召回线程池超时 + 优雅关闭
- RAG 缓存线程安全（TTLCache + Lock）
- BM25 索引线程安全（RLock）
- ASR 端点速率限制（10次/60s）

### 变更
- MySQL 连接超时防 DB 卡死（connect_timeout=10, read/write_timeout=30）

---

## [1.0.0] - 2026-08-20

### 核心功能
- RAG 智能检索：双路并行召回（Milvus 向量 + BM25）+ RRF 合并 + Reranker 精排
- Agent 预处理流水线：清洗 → 规整/分类 → HyDE 改写
- ASR 语音识别：FunASR + WebSocket 流式 + 领域纠错
- 5 角色 RBAC：superadmin / admin / ops / service / dept
- JWT 认证 + 模拟登录（超管专用）
- 定时任务调度：APScheduler + 工单同步 + 清理 + 告警检查
- 异常告警机制：指标采集 + 6 条规则 + 站内告警 + webhook
- 数据库：12 表 + Milvus 向量集合
- API：52 个端点
- 前端：Vue3 + Element Plus + ECharts + Pinia

### 测试
- 后端：59 文件 / 1240 用例 / 13 集成测试 / 5 基准测试
- 前端：58 文件 / 681 用例 / 3 E2E spec / 3 契约测试
- CI：9 个 job（lint + test + typecheck + e2e + contract + benchmark + build）