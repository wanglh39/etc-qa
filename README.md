# ETC客服QA智能检索系统

基于 Milvus 向量数据库 + MySQL + LangGraph Agent 的 ETC 客服 QA 智能检索系统。

## 项目结构

```
etc-qa/
├── backend/                # 后端 (FastAPI + Python)
│   ├── api/                # API 路由 + 认证
│   ├── agent/              # LangGraph Agent 流水线
│   ├── asr/                # 语音识别服务 (WebSocket 流式)
│   ├── alert/              # 告警监控 + 通知
│   ├── config/             # 配置文件 (数据库/模型/Agent/RAG)
│   ├── db/                 # MySQL + Milvus 客户端
│   ├── models/             # Pydantic 数据模型
│   ├── prompt/             # 提示词模板管理
│   ├── rag/                # RAG 检索 (向量+BM25+Reranker)
│   ├── scheduler/          # 定时任务调度
│   ├── scripts/            # 初始化/评估/维护脚本
│   ├── tests/              # 单元测试 + 集成测试 + 基准测试
│   └── utils/              # JWT/配置/日志/权限 工具
│
├── frontend/               # 前端 (Vue3 + Element Plus + TypeScript)
│   ├── src/
│   │   ├── api/            # API 调用层
│   │   ├── pages/          # 页面组件
│   │   │   ├── workbench/  # 管理工作台 (看板/审核/分类/配置/账号/角色/运维)
│   │   │   ├── service/    # 客服工作台
│   │   │   └── dept/       # 部门工单处理
│   │   ├── components/     # 通用组件
│   │   ├── router/         # 路由配置
│   │   ├── store/          # Pinia 状态管理
│   │   └── utils/          # Axios 实例 + 工具函数
│   ├── tests/              # 单元测试 + 契约测试
│   └── e2e/                # E2E 测试 (Playwright)
│
├── docs/                   # 项目文档
└── .github/workflows/      # CI/CD (ci.yml)
```

## 技术栈

| 层级 | 后端 | 前端 |
|------|------|------|
| 框架 | FastAPI + Uvicorn | Vue3 + Vite |
| 语言 | Python 3.10 | TypeScript |
| 数据库 | MySQL 8.x + Milvus Lite | — |
| UI | — | Element Plus |
| 状态管理 | — | Pinia |
| 图表 | — | ECharts |
| Embedding | bge-large-zh-v1.5 (1024维) | — |
| Reranker | bge-reranker-large | — |
| LLM | DeepSeek Chat | — |
| Agent | LangGraph 状态图编排 | — |
| BM25 | jieba + rank_bm25 | — |
| 认证 | JWT (PyJWT) + RBAC | Axios 拦截器 + 路由守卫 |
| 测试 | pytest + pytest-benchmark | vitest + Playwright |
| CI | GitHub Actions (9 jobs) | — |

---

## 角色体系（5角色 RBAC）

| 角色 | 定位 | 默认账号 | 默认首页 |
|------|------|---------|---------|
| superadmin | 超级管理员（账号/角色/日志） | superadmin / 123456 | /workbench/admin/account |
| admin | 业务管理员（内容+审核+配置） | admin / 123456 | /workbench/admin/dashboard |
| ops | 运维工程师（监控+调度+告警） | ops / 123456 | /workbench/admin/status |
| service | 客服（一线问答） | service / 123456 | /service |
| dept | 部门处理员（工单处理） | dept / 123456 | /dept/handle/{dept} |

---

## 环境初始化

### 1. 后端

```bash
cd backend

# 创建 conda 环境
conda create -n etc_qa python=3.10 -y
conda activate etc_qa

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY

# 配置模型路径 (修改 config/models.yaml 中的路径为你本机路径)

# 初始化数据库 (需要 MySQL 运行中)
python scripts/data/init_db.py test
python scripts/data/init_config.py test

# 启动
python main.py
# 默认监听 http://0.0.0.0:8000
```

### 2. 前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
# 默认监听 http://localhost:5173
# Vite 自动代理 /api → http://localhost:8000
```

### 3. 开发登录

浏览器打开 `http://localhost:5173/dev-login.html` 自动注入 service 角色 token 跳转工作台。

或访问 `http://localhost:5173/login` 手动登录（见上方角色表）。

---

## API 端点汇总（52个）

**Base URL:** `http://localhost:8000/api`

所有需认证的接口在 Header 中携带 `Authorization: Bearer <token>`（通过 `/api/auth/login` 获取）。

### 认证（3个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 1 | POST | /api/auth/login | 公开 | 登录获取 JWT |
| 2 | GET | /api/auth/verify | 已登录 | 验证 token 有效性 |
| 3 | POST | /api/auth/impersonate | superadmin | 模拟登录为其他角色 |

### QA 检索与知识管理（8个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 4 | POST | /api/query | 已登录 | RAG 语义检索 |
| 5 | POST | /api/add | admin, superadmin | 新增知识并更新索引 |
| 6 | POST | /api/agent/process | 已登录 | Agent 入库结构化处理 |
| 7 | GET | /api/qa/list | 已登录 | QA 分页列表 |
| 8 | GET | /api/qa/{id} | 已登录 | QA 详情 |
| 9 | POST | /api/qa/search | 已登录 | 关键词搜索 |
| 10 | PUT | /api/qa/status | admin, superadmin | 修改 QA 状态 |
| 11 | DELETE | /api/qa/{id} | admin, superadmin | 删除 QA |

### 配置管理（3个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 12 | GET | /api/config/{key} | admin, superadmin | 读取配置 |
| 13 | PUT | /api/config/{key} | admin, superadmin | 更新配置 |
| 14 | POST | /api/config/reload | admin, superadmin | 刷新配置缓存 |

### 分类管理（4个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 15 | GET | /api/categories | 已登录 | 分类树 |
| 16 | POST | /api/categories | admin, superadmin | 创建分类 |
| 17 | PUT | /api/categories/{id} | admin, superadmin | 更新分类 |
| 18 | DELETE | /api/categories/{id} | admin, superadmin | 删除分类 |

### 统计与审核（3个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 19 | GET | /api/stats | admin, superadmin, ops | 聚合统计 |
| 20 | GET | /api/stats/trend | admin, superadmin, ops | 趋势统计 |
| 21 | GET | /api/audit/history | admin, superadmin | 审核历史 |

### 工单管理（5个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 22 | GET | /api/work_orders | 已登录 | 工单列表 |
| 23 | GET | /api/work_orders/stats | 已登录 | 工单状态统计 |
| 24 | POST | /api/work_orders | 已登录 | 创建工单 |
| 25 | GET | /api/work_orders/{id} | 已登录 | 工单详情 |
| 26 | PUT | /api/work_orders/{id}/reply | 已登录 | 工单回复/办结 |

### ASR 语音（3个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 27 | POST | /api/asr | 已登录 | 语音转文字 |
| 28 | GET | /api/asr/health | 已登录 | ASR 健康检查 |
| 29 | POST | /api/asr/query | 已登录 | ASR + 检索一体化 |

### 用户管理（5个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 30 | GET | /api/users | superadmin | 用户列表 |
| 31 | POST | /api/users | superadmin | 创建用户 |
| 32 | PUT | /api/users/{id} | superadmin | 更新用户 |
| 33 | PUT | /api/users/{id}/password | superadmin | 重置密码 |
| 34 | DELETE | /api/users/{id} | superadmin | 删除用户 |

### 角色与权限（5个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 35 | GET | /api/roles/permissions | 已登录 | 当前用户权限 |
| 36 | GET | /api/roles | superadmin | 角色列表 |
| 37 | POST | /api/roles | superadmin | 创建角色 |
| 38 | PUT | /api/roles/{id} | superadmin | 更新角色 |
| 39 | DELETE | /api/roles/{id} | superadmin | 删除角色 |

### 操作日志（1个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 40 | GET | /api/operations | superadmin | 操作日志列表 |

### 定时调度（4个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 41 | GET | /api/scheduler/status | admin, superadmin, ops | 调度器状态 |
| 42 | POST | /api/scheduler/trigger/{job_id} | admin, superadmin, ops | 手动触发任务 |
| 43 | PUT | /api/scheduler/config | superadmin, ops | 修改调度周期 |
| 44 | GET | /api/scheduler/logs | admin, superadmin, ops | 调度日志 |

### 告警管理（3个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 45 | GET | /api/alerts | admin, superadmin, ops | 告警列表 |
| 46 | PUT | /api/alerts/{id}/ack | admin, superadmin, ops | 确认告警 |
| 47 | GET | /api/alerts/metrics | admin, superadmin, ops | 监控指标 |

### 系统运维（2个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 48 | GET | /api/system/status | superadmin, ops | 组件健康状态 |
| 49 | GET | /api/system/logs | superadmin, ops | 应用日志 |

### 健康检查（1个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 50 | GET | /api/health | 公开 | 服务健康检查 |

### WebSocket（1个）

| # | 方法 | 路径 | 说明 |
|---|------|------|------|
| 51 | WS | /ws/asr/stream | 流式 ASR 识别 + 自动检索 |

### 数据库表（1个）

| # | 方法 | 路径 | 权限 | 说明 |
|---|------|------|------|------|
| 52 | GET | /api/categories | 已登录 | （分类树，与15相同接口） |

> 实际独立端点 51 个（含 WebSocket），上表按功能模块分组列出。

---

## 测试

### 后端测试

```bash
cd backend
# 单元测试
python -m pytest tests/ -x -q -o addopts="" --ignore=tests/integration
# 全量测试（含集成测试）
python -m pytest tests/ -x -q
# 基准测试
python -m pytest tests/benchmark/ -q
```

- 测试文件：59 个
- 测试用例：1240 个
- 集成测试：13 个文件
- 基准测试：5 个

### 前端测试

```bash
cd frontend
# 单元测试 + 覆盖率
npm run test
# E2E 测试
npx playwright test
# 类型检查
npx vue-tsc --noEmit
# Lint
npm run lint
```

- 单元测试文件：58 个，用例 681 个
- 覆盖率：语句 95.99% / 分支 87.66% / 函数 81.49% / 行 95.99%
- E2E 测试：3 个 spec，8 个用例
- 契约测试：3 个用例（OpenAPI 契约）

### CI/CD

GitHub Actions 统一 CI（`.github/workflows/ci.yml`），9 个 job：
后端 lint → 后端测试 → 前端 lint → 前端测试 → 前端类型检查 → E2E 测试 → 契约测试 → 基准测试 → 前端构建。

---

## 文档索引

### 根目录

| 文档 | 说明 |
|------|------|
| [CHANGELOG.md](CHANGELOG.md) | 变更日志 |
| [CONTRIBUTING.md](CONTRIBUTING.md) | 贡献指南 |

### docs/architecture/ — 架构设计

| 文档 | 说明 |
|------|------|
| [系统总体架构图.md](docs/architecture/系统总体架构图.md) | 系统总体架构（ASCII） |
| [架构图-Mermaid.md](docs/architecture/架构图-Mermaid.md) | 架构图（Mermaid 渲染版） |
| [后端架构图.md](docs/architecture/后端架构图.md) | 后端架构 |
| [前端架构图.md](docs/architecture/前端架构图.md) | 前端架构 |
| [后端技术设计.md](docs/architecture/后端技术设计.md) | 后端技术文档 |
| [前端技术设计.md](docs/architecture/前端技术设计.md) | 前端技术文档 |
| [后端目录结构.md](docs/architecture/后端目录结构.md) | 后端目录结构 |
| [前端目录结构.md](docs/architecture/前端目录结构.md) | 前端目录结构 |
| [高并发演进路线.md](docs/architecture/高并发演进路线.md) | 并发演进规划 |
| [adr/](docs/architecture/adr/) | 架构决策记录（ADR-001~005） |

### docs/api/ — API 文档

| 文档 | 说明 |
|------|------|
| [API接口文档.md](docs/api/API接口文档.md) | API 手写文档（52 端点） |
| [openapi.json](docs/api/openapi.json) | OpenAPI Schema（自动生成） |

### docs/database/ — 数据库设计

| 文档 | 说明 |
|------|------|
| [数据库设计文档.md](docs/database/数据库设计文档.md) | 12 表 + Milvus 集合 |

### docs/security/ — 安全设计

| 文档 | 说明 |
|------|------|
| [安全设计文档.md](docs/security/安全设计文档.md) | RBAC + JWT + 模拟登录 + 数据安全 |

### docs/ops/ — 运维手册

| 文档 | 说明 |
|------|------|
| [运维手册.md](docs/ops/运维手册.md) | Runbook + 故障处理 + 告警规则 + 监控指标 |

### docs/guides/ — 指南

| 文档 | 说明 |
|------|------|
| [开发环境搭建.md](docs/guides/开发环境搭建.md) | 环境搭建 |
| [部署指南.md](docs/guides/部署指南.md) | 部署指南 |
| [交接清单.md](docs/guides/交接清单.md) | 交接清单 |

### docs/standards/ — 规范

| 文档 | 说明 |
|------|------|
| [开发规范.md](docs/standards/开发规范.md) | 代码规范 + Git 规范 |
| [数据规范.md](docs/standards/数据规范.md) | 数据规范 |

### docs/testing/ — 测试

| 文档 | 说明 |
|------|------|
| [测试体系文档.md](docs/testing/测试体系文档.md) | 测试体系说明 |

### docs/tutorials/ — 教程

| 文档 | 说明 |
|------|------|
| [Docker使用教程.md](docs/tutorials/Docker使用教程.md) | Docker 使用指南 |
| [Git使用教程.md](docs/tutorials/Git使用教程.md) | Git 使用指南 |
| [AI交互脚本.md](docs/tutorials/AI交互脚本.md) | AI 交互脚本 |
