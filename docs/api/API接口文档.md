# API 接口文档

基础路径：`/api`

认证方式：JWT Bearer Token。除 `/api/auth/login` 和 `/api/health` 外，所有接口需在 Header 中携带 `Authorization: Bearer <token>`。

角色权限：5 角色 RBAC（superadmin / admin / ops / service / dept）。各端点权限见下表"权限"列，未标注角色的端点仅需已登录。

---

## 1. 认证模块

### POST /api/auth/login — 登录

权限：公开

```json
// Request
{ "username": "admin", "password": "dev123456" }

// Response
{ "access_token": "eyJ...", "token_type": "bearer", "role": "admin", "dept": "" }
```

Token 有效期 24 小时。限流：30次/60s/IP、5次/60s/用户。

### GET /api/auth/verify — 验证 Token

权限：已登录

```json
// Response
{ "valid": true, "user": { "username": "admin", "role": "admin", "dept": "" } }
```

### POST /api/auth/impersonate — 模拟登录

权限：superadmin

```json
// Request
{ "target_username": "service" }

// Response
{ "access_token": "eyJ...", "token_type": "bearer", "role": "service", "dept": "", "impersonating": true }
```

超管模拟其他角色身份，写操作日志。

---

## 2. QA 检索与知识管理

### POST /api/query — RAG 语义检索

权限：已登录（限流 30次/60s）

```json
// Request
{ "question": "ETC设备如何更换绑定手机号", "category_l1": null }

// Response
{
  "query": "ETC设备如何更换绑定手机号",
  "standardized_query": "ETC设备更换绑定手机号",
  "confidence": "high",
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

| confidence | 分数范围 | 返回数量 | 是否创建工单 |
|------------|---------|---------|------------|
| high | >=0.8 | Top-3 | 否 |
| mid | 0.5~0.8 | Top-5 | 否 |
| low | 0.2~0.5 | Top-10 | 是 |
| none | <0.2 | 空 | 是 |

### POST /api/add — 新增知识

权限：admin, superadmin

```json
// Request
{ "question": "...", "answer": "...", "category_l1": "...", "category_l2": "...", "internal_process": "...", "feedback_dept": "..." }

// Response
{ "qa_id": 105, "message": "添加成功，索引已更新" }
```

### POST /api/agent/process — Agent 入库结构化处理

权限：已登录（限流 20次/60s）

```json
// Request
{ "question": "原始问题", "answer": "", "context": "", "user_id": "" }

// Response
{
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

### GET /api/qa/list — QA 分页列表

权限：已登录

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数 (1-100) |
| category_l1 | string | — | 一级分类过滤 |
| status | string | — | 状态过滤 (active/deprecated/archived) |

```json
// Response
{ "items": [...], "total": 100, "page": 1, "page_size": 20 }
```

### GET /api/qa/{qa_id} — QA 详情

权限：已登录。404 表示不存在。

### POST /api/qa/search — 关键词搜索

权限：已登录

```json
// Request
{ "keyword": "验证码", "category_l1": null, "status": null, "page": 1, "page_size": 20 }
```

### PUT /api/qa/status — 修改状态

权限：admin, superadmin。合法状态：active / deprecated / archived。

```json
// Request
{ "qa_id": 1, "status": "deprecated" }

// Response
{ "qa_id": 1, "status": "deprecated", "message": "状态已更新为deprecated" }
```

### DELETE /api/qa/{qa_id} — 删除 QA

权限：admin, superadmin。404 表示不存在。

---

## 3. 配置管理

### GET /api/config/{key} — 读取配置

权限：admin, superadmin（敏感字段脱敏）

```json
// Response
{ "key": "qa_statuses", "value": ["active", "deprecated", "archived"] }
```

### PUT /api/config/{key} — 更新配置

权限：admin, superadmin

```json
// Request
{ "value": ["active", "deprecated"], "description": "可选描述" }

// Response
{ "key": "qa_statuses", "message": "配置已更新，缓存已刷新" }
```

### POST /api/config/reload — 刷新配置缓存

权限：admin, superadmin

可配置的 key：forbidden_new_kws / must_preserve_kws / brand_keywords / subject_keywords / question_words / preserve_question_words / filler_patterns / core_patterns / clean_rules / qa_statuses

---

## 4. 分类管理

### GET /api/categories — 分类树

权限：已登录

```json
// Response
{
  "categories": [
    { "id": 1, "label": "登录账号类", "parentId": null, "children": [
      { "id": 11, "label": "登录失败", "parentId": 1 }
    ]}
  ]
}
```

### POST /api/categories — 创建分类

权限：admin, superadmin

```json
// Request
{ "label": "新分类", "parent_id": 1, "description": "说明" }
```

### PUT /api/categories/{cat_id} — 更新分类

权限：admin, superadmin

### DELETE /api/categories/{cat_id} — 删除分类

权限：admin, superadmin

---

## 5. 统计与审核

### GET /api/stats — 聚合统计

权限：admin, superadmin, ops

```json
// Response
{
  "qa_total": 200, "qa_active": 150, "qa_deprecated": 30, "qa_archived": 20,
  "work_order_total": 50, "work_order_submitted": 30, "work_order_processed": 15,
  "category_stats": { "登录账号类": 80, "订单支付类": 60 }
}
```

### GET /api/stats/trend — 趋势统计

权限：admin, superadmin, ops

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| days | int | 7 | 统计天数 |

### GET /api/audit/history — 审核历史

权限：admin, superadmin

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数 |

---

## 6. 工单管理

### GET /api/work_orders — 工单列表

权限：已登录（dept 角色可按 dept 参数查看对应部门，不再强制限定本部门）

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数 |
| status | string | — | submitted/answered/processed |
| dept | string | — | 按部门过滤（aftersale/ops/finance/market/human） |

### GET /api/work_orders/stats — 工单状态统计

权限：已登录（可传 dept 参数统计对应部门；不传则统计全部）

### POST /api/work_orders — 创建工单

权限：已登录（自动生成 external_id）

### GET /api/work_orders/{wo_id} — 工单详情

权限：已登录

### PUT /api/work_orders/{wo_id}/reply — 工单回复/办结

权限：已登录

---

## 7. ASR 语音识别

### POST /api/asr — 语音转文字

权限：已登录（限流 10次/60s）

```
Request: multipart/form-data, file 字段为音频文件
Response: { "text": "识别结果", "confidence": 0.95, "duration_ms": 3200, "model": "alicloud-nls", "language": "zh" }
```

### GET /api/asr/health — ASR 健康检查

权限：已登录

```json
// Response
{ "loaded": true, "model": "alicloud-nls", "mode": "alicloud", "hotwords_id": "xxx" }
```

### POST /api/asr/query — ASR + 检索一体化

权限：已登录（限流 10次/60s）

上传音频 → ASR 识别 → RAG 检索 → 返回候选答案。

---

## 8. 用户管理

### GET /api/users — 用户列表

权限：superadmin

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数 |
| role | string | — | 角色过滤 |
| status | string | — | 状态过滤 |

### POST /api/users — 创建用户

权限：superadmin（写操作日志）

```json
// Request
{ "username": "newuser", "password": "your_password", "role": "service", "dept": "aftersale" }
```

### PUT /api/users/{user_id} — 更新用户

权限：superadmin（可修改角色/部门/状态）

### PUT /api/users/{user_id}/password — 重置密码

权限：superadmin

### DELETE /api/users/{user_id} — 删除用户

权限：superadmin

---

## 9. 角色与权限

### GET /api/roles/permissions — 当前用户权限

权限：已登录（返回当前用户自己的权限列表）

### GET /api/roles — 角色列表

权限：superadmin

### POST /api/roles — 创建角色

权限：superadmin

```json
// Request
{ "role_key": "newrole", "role_name": "新角色", "description": "说明", "permissions": ["dashboard"] }
```

### PUT /api/roles/{role_id} — 更新角色

权限：superadmin

### DELETE /api/roles/{role_id} — 删除角色

权限：superadmin

---

## 10. 操作日志

### GET /api/operations — 操作日志列表

权限：superadmin

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数 |
| operator | string | — | 操作人过滤 |
| action | string | — | 操作类型过滤 |

---

## 11. 定时调度

### GET /api/scheduler/status — 调度器状态

权限：admin, superadmin, ops（返回运行状态与任务列表）

### POST /api/scheduler/trigger/{job_id} — 手动触发任务

权限：admin, superadmin, ops

### PUT /api/scheduler/config — 修改调度周期

权限：superadmin, ops

```json
// Request
{ "job_id": "sync_work_orders", "hours": 2, "minutes": 0 }
```

### GET /api/scheduler/logs — 调度日志

权限：admin, superadmin, ops

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数 |

---

## 12. 告警管理

### GET /api/alerts — 告警事件列表

权限：admin, superadmin, ops

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| page | int | 1 | 页码 |
| page_size | int | 20 | 每页条数 |
| status | string | — | active/acked |
| severity | string | — | critical/warning/info |

### PUT /api/alerts/{alert_id}/ack — 确认告警

权限：admin, superadmin, ops

### GET /api/alerts/metrics — 监控指标

权限：admin, superadmin, ops（返回全部监控指标当前值）

---

## 13. 系统运维

### GET /api/system/status — 组件健康状态

权限：superadmin, ops

```json
// Response
{
  "api": "ok",
  "mysql": "ok",
  "milvus": "ok",
  "rag": "ok",
  "asr": "ok",
  "scheduler": "running",
  "alert": "ok"
}
```

### GET /api/system/logs — 应用日志

权限：superadmin, ops

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| lines | int | 100 | 返回行数 |
| level | string | — | INFO/WARNING/ERROR 过滤 |

---

## 14. 健康检查

### GET /api/health — 服务健康检查

权限：公开

```json
// Response
{ "status": "ok" }
```

---

## 15. WebSocket

### WS /ws/asr/stream — 流式 ASR 识别

流式 ASR 识别 + 自动检索。支持控制消息：config / flush / clear_cache / clear_context / select_answer / reset。

---

## 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或 token 失效 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 429 | 请求限流 |
| 500 | 服务器内部错误 |
