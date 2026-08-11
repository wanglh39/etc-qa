# ETC客服QA智能检索系统

基于 Milvus 向量数据库 + MySQL + LangGraph Agent 的 ETC 客服 QA 智能检索系统。

## 项目结构

```
etc-qa/
├── backend/                # 后端 (FastAPI + Python)
│   ├── api/                # API 路由 + 认证
│   ├── agent/              # LangGraph Agent 流水线
│   ├── asr/                # 语音识别服务
│   ├── config/             # 配置文件 (数据库/模型/Agent/RAG)
│   ├── db/                 # MySQL + Milvus 客户端
│   ├── models/             # Pydantic 数据模型
│   ├── prompt/             # Prompt 版本管理 + Shadow 测试
│   ├── rag/                # RAG 检索 (向量+BM25+Reranker)
│   ├── scripts/            # 初始化/评估/维护脚本
│   ├── tests/              # 单元测试 + 集成测试
│   └── utils/              # JWT/配置/日志 工具
│
└── frontend/               # 前端 (Vue3 + Element Plus + TypeScript)
    └── src/
        ├── api/            # API 调用层 (auth/workbench/knowledge/dashboard/audit/system)
        ├── pages/          # 页面组件
        │   ├── workbench/  # 智能问答工作台
        │   ├── audit/      # 审核列表 + 详情
        │   ├── dashboard/  # 数据看板
        │   ├── category/   # 分类管理
        │   ├── service/    # 工单管理
        │   └── system/     # 系统配置
        ├── components/     # 通用组件
        ├── router/         # 路由配置
        ├── store/          # Pinia 状态管理
        └── utils/          # Axios 实例 + 拦截器
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
| LLM | DeepSeek Chat / DeepSeek V4 Pro | — |
| Agent | LangGraph 状态图编排 | — |
| BM25 | jieba + rank_bm25 | — |
| 认证 | JWT (PyJWT) | Axios 拦截器 |

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

或访问 `http://localhost:5173/login` 手动登录：

| 账号 | 密码 | 角色 | 默认页面 |
|------|------|------|---------|
| admin | 123456 | 管理员 | 待审核列表 |
| service | 123456 | 客服 | 智能问答工作台 |
| dept | 123456 | 部门 | 部门工单处理 |

---

# API 接口文档

**Base URL:** `http://localhost:8000/api`

所有需要认证的接口在 Header 中携带 `Authorization: Bearer <token>`（通过 `/api/auth/login` 获取）。

---

## 1. 认证

### POST /api/auth/login — 登录

```
Request:  { "username": "admin", "password": "123456" }
Response: { "access_token": "eyJ...", "token_type": "bearer", "role": "admin", "dept": "" }
```

无需认证。返回的 token 有效期 24 小时。

---

## 2. 核心 QA 检索

### POST /api/query — 语义检索

```
Request:  { "question": "ETC设备如何更换绑定手机号", "category_l1": null }
Response: {
  "query": "ETC设备如何更换绑定手机号",
  "standardized_query": "ETC设备更换绑定手机号",
  "confidence": "high",       // high | mid | low | none
  "total_candidates": 3,
  "candidates": [
    {
      "qa_id": 101,
      "question": "ETC设备绑定的手机号如何更换？",
      "answer": "请用户打开ETC App → 我的 → 设备管理 → ...",
      "category_l1": "登录账号类",
      "category_l2": "手机号变更",
      "internal_process": null,
      "feedback_dept": null,
      "score": 0.923
    }
  ],
  "work_order_id": null
}
```

需要认证。

### POST /api/add — 新增知识条目

```
Request:  { "question": "...", "answer": "...", "category_l1": "...", "category_l2": "..." }
Response: { "qa_id": 105, "message": "添加成功，索引已更新" }
```

需要认证。

### POST /api/agent/process — Agent 预处理流水线

```
Request:  { "question": "原始问题", "answer": "", "context": "", "user_id": "" }
Response: {
  "question": "标准化后的问题",
  "answer": "生成的标准答案",
  "internal_process": "", "feedback_dept": "",
  "is_duplicate": false, "duplicate_of": null,
  "similarity_score": 0.0,
  "category_l1": "登录账号类", "category_l2": "手机号变更",
  "category_confidence": 0.85,
  "needs_review": false, "review_highlights": [],
  "current_step": "done", "error": null
}
```

需要认证。

---

## 3. 知识库 CRUD

### GET /api/qa/list — 分页列表

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数 (1-100) |
| category_l1 | string | — | 一级分类过滤 |
| status | string | — | 状态过滤 (active/deprecated/archived) |

```
Response: {
  "items": [{ "id": 1, "question": "...", "answer": "...", "category_l1": "...", "category_l2": "...", "status": "active", "created_at": "..." }],
  "total": 100, "page": 1, "page_size": 20
}
```

需要认证。

### GET /api/qa/{qa_id} — 详情

```
Response: {
  "id": 1, "question": "...", "answer": "...",
  "category_l1": "...", "category_l2": "...",
  "internal_process": "...", "feedback_dept": "...",
  "status": "active", "created_at": "...", "updated_at": "..."
}
```

需要认证。404 表示不存在。

### POST /api/qa/search — 关键词搜索

```
Request:  { "keyword": "验证码", "category_l1": null, "status": null, "page": 1, "page_size": 20 }
Response: 同 GET /api/qa/list
```

需要认证。

### PUT /api/qa/status — 修改状态

```
Request:  { "qa_id": 1, "status": "deprecated" }
Response: { "qa_id": 1, "status": "deprecated", "message": "状态已更新为deprecated" }
```

合法状态: `active`, `deprecated`, `archived`。需要认证。

### DELETE /api/qa/{qa_id} — 删除

```
Response: { "qa_id": 1, "message": "已删除" }
```

需要认证。404 表示不存在。

---

## 4. 统计与分类

### GET /api/stats — 聚合统计

```
Response: {
  "qa_total": 200, "qa_active": 150, "qa_deprecated": 30, "qa_archived": 20,
  "work_order_total": 50, "work_order_submitted": 30, "work_order_processed": 15,
  "category_stats": { "登录账号类": 80, "订单支付类": 60, "系统功能类": 60 }
}
```

需要认证。

### GET /api/categories — 分类树

```
Response: {
  "categories": [
    { "id": 1, "label": "登录账号类", "parentId": null, "children": [
      { "id": 11, "label": "登录失败", "parentId": 1 }
    ]}
  ]
}
```

需要认证。

---

## 5. 工单

### GET /api/work_orders — 工单列表

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数 |
| status | string | — | submitted/answered/processed |

```
Response: {
  "items": [{ "id": 1, "external_id": "WO-20260701-0001", "raw_data": "{...}", "status": "submitted", "created_at": "..." }],
  "total": 10, "page": 1, "page_size": 20
}
```

需要认证。

---

## 6. 业务配置

### GET /api/config/{key} — 读取配置

```
Response: { "key": "qa_statuses", "value": ["active", "deprecated", "archived"] }
```

需要认证。

### PUT /api/config/{key} — 更新配置

```
Request:  { "value": ["active", "deprecated"], "description": "可选描述" }
Response: { "key": "qa_statuses", "message": "配置已更新，缓存已刷新" }
```

需要认证。

### POST /api/config/reload — 刷新缓存

```
Response: { "message": "所有配置缓存已刷新，将从DB重新加载" }
```

需要认证。

---

## 7. Prompt 版本管理

### GET /api/prompts — 列出所有 Prompt Key

```
Response: [{ "prompt_key": "standardize", "latest_version": 3, "active_count": 1, "shadow_count": 1 }]
```

需要认证。

### GET /api/prompts/{key}/versions — 版本列表

```
Response: [{ "id": 1, "prompt_key": "standardize", "version": 1, "is_active": 1, "status": "active", "description": "", "template_text_preview": "前100字符..." }]
```

需要认证。

### GET /api/prompts/{key}/versions/{version} — 完整版本内容

需要认证。

### POST /api/prompts/publish — 发布新版本

```
Request:  { "prompt_key": "standardize", "template_text": "完整模板...", "description": "修复了xxx问题" }
```

需要认证。

### POST /api/prompts/rollback — 回滚版本

```
Request:  { "prompt_key": "standardize", "target_version": 2 }
```

需要认证。

---

## 8. ASR 语音识别

### POST /api/asr — 语音转文字

```
Request:  multipart/form-data, file 字段为音频文件
Response: { "text": "识别结果", "confidence": 0.95, "duration_ms": 3200, "model": "funasr-nano-2512", "language": "zh" }
```

需要认证。

### GET /api/asr/health — ASR 健康检查

```
Response: { "loaded": true, "model": "funasr-nano-2512", "device": "cpu", "finetuned": false }
```

---

## 9. 健康检查

### GET /api/health

```
Response: { "status": "ok" }
```

无需认证。

---

# API 端点汇总

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 1 | POST | /api/auth/login | 否 | 登录获取 JWT |
| 2 | POST | /api/query | 是 | 语义检索 QA |
| 3 | POST | /api/add | 是 | 新增知识 |
| 4 | POST | /api/agent/process | 是 | Agent 预处理 |
| 5 | GET | /api/qa/list | 是 | QA 分页列表 |
| 6 | GET | /api/qa/{id} | 是 | QA 详情 |
| 7 | POST | /api/qa/search | 是 | 关键词搜索 |
| 8 | PUT | /api/qa/status | 是 | 修改状态 |
| 9 | DELETE | /api/qa/{id} | 是 | 删除知识 |
| 10 | GET | /api/stats | 是 | 聚合统计 |
| 11 | GET | /api/categories | 是 | 分类树 |
| 12 | GET | /api/work_orders | 是 | 工单列表 |
| 13 | GET | /api/config/{key} | 是 | 读取配置 |
| 14 | PUT | /api/config/{key} | 是 | 更新配置 |
| 15 | POST | /api/config/reload | 是 | 刷新配置缓存 |
| 16 | GET | /api/prompts | 是 | Prompt Key 列表 |
| 17 | GET | /api/prompts/{key}/versions | 是 | 版本列表 |
| 18 | GET | /api/prompts/{key}/versions/{v} | 是 | 版本详情 |
| 19 | POST | /api/prompts/publish | 是 | 发布新版本 |
| 20 | POST | /api/prompts/rollback | 是 | 回滚版本 |
| 21 | POST | /api/prompts/shadow/start | 是 | 开启 Shadow 测试 |
| 22 | POST | /api/prompts/shadow/stop | 是 | 停止 Shadow 测试 |
| 23 | GET | /api/prompts/shadow/stats | 是 | Shadow 统计 |
| 24 | GET | /api/prompts/shadow/records | 是 | Shadow 记录 |
| 25 | POST | /api/asr | 是 | 语音转文字 |
| 26 | GET | /api/asr/health | 是 | ASR 健康检查 |
| 27 | GET | /api/health | 否 | 服务健康检查 |

---

# 待测试项

## 后端初始化

- [ ] MySQL 8.x 已安装并运行 (端口 3306)
- [ ] 编辑 `.env` 填入有效的 `DEEPSEEK_API_KEY`
- [ ] 修改 `config/models.yaml` 中的模型路径为本机实际路径
- [ ] 下载模型: `bge-large-zh-v1.5` + `bge-reranker-large`
- [ ] `python scripts/data/init_db.py test` — 建表 + 导入 CSV + 创建 Milvus 向量
- [ ] `python scripts/data/init_config.py test` — 导入业务配置
- [ ] `python main.py` — 后端无报错启动
- [ ] `curl http://localhost:8000/api/health` → `{"status":"ok"}`

## 认证

- [ ] `POST /api/auth/login` — admin/123456 返回 token + role=admin
- [ ] `POST /api/auth/login` — service/123456 返回 token + role=service
- [ ] `POST /api/auth/login` — 错误密码返回 401
- [ ] 无 token 访问 `/api/query` → 401

## QA 检索

- [ ] `POST /api/query` — 输入已知问题 → 返回候选列表 score > 0.5
- [ ] `POST /api/query` — 输入无关问题 → confidence=none
- [ ] 候选结果按 score 降序排列
- [ ] standardized_query 标准化正确

## 知识库 CRUD

- [ ] `GET /api/qa/list` — 分页加载正常
- [ ] `GET /api/qa/list?status=active` — 状态过滤
- [ ] `GET /api/qa/list?category_l1=登录账号类` — 分类过滤
- [ ] `POST /api/qa/search` — 关键词搜索匹配
- [ ] `GET /api/qa/{id}` — 详情加载
- [ ] `POST /api/add` — 新增后列表中可见
- [ ] `PUT /api/qa/status` — 状态变更生效
- [ ] `DELETE /api/qa/{id}` — 删除后列表中消失

## Agent 流水线

- [ ] `POST /api/agent/process` — 返回分类结果 (category_l1/category_l2)
- [ ] `POST /api/agent/process` — 重复检测 (is_duplicate)
- [ ] `POST /api/agent/process` — 审核标记 (needs_review)

## 统计

- [ ] `GET /api/stats` — qa_total/active/deprecated 数字正确
- [ ] `GET /api/stats` — work_order 统计正确
- [ ] `GET /api/stats` — category_stats 包含所有分类

## 分类

- [ ] `GET /api/categories` — 返回树形结构，与 qa_pairs 数据一致

## 工单

- [ ] `GET /api/work_orders` — 分页列表正常
- [ ] `GET /api/work_orders?status=submitted` — 状态过滤

## 配置管理

- [ ] `GET /api/config/qa_statuses` — 返回状态列表
- [ ] `PUT /api/config/qa_statuses` — 更新后 `GET` 读到新值
- [ ] `POST /api/config/reload` — 缓存刷新

## Prompt 管理

- [ ] `GET /api/prompts` — 列出已有 prompt key
- [ ] `POST /api/prompts/publish` — 发布新版本成功
- [ ] `POST /api/prompts/rollback` — 回滚到指定版本

## ASR (可选)

- [ ] `GET /api/asr/health` — loaded=true (需下载模型)
- [ ] `POST /api/asr` — 上传音频 → 返回识别文字

### 前端页面

- [ ] 登录页: 3 种角色登录跳转正确
- [ ] 智能问答工作台: 搜索 → 展示标准化问题 + 候选答案卡片
- [ ] 智能问答工作台: 无匹配 → 提交 Agent 处理 → 展示处理结果
- [ ] 数据看板: 4 个指标卡片 + 饼图展示真实数据
- [ ] 分类管理: 加载真实分类树
- [ ] CRM 工单列表: 分页加载 + 状态筛选
- [ ] 待审核列表: 加载 deprecated 状态知识 + 入库/驳回操作
- [ ] 审核详情: 展示完整知识信息 + 入库/驳回
- [ ] 系统配置: 查看/编辑配置项 + 刷新缓存
