# API 接口文档

基础路径：`/api/v1`

---

## 1. 智能问答

### POST /query

客服输入问题，返回最匹配的答案话术。

**请求体：**

```json
{
  "question": "ETC扣费异常怎么处理",
  "category_l1": null
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question | string | 是 | 客服输入的原始问题 |
| category_l1 | string | 否 | 限定一级分类（暂未实现分类过滤） |

**响应体：**

```json
{
  "query": "ETC扣费异常怎么处理",
  "standardized_query": "ETC扣费异常如何处理",
  "confidence": "high",
  "candidates": [
    {
      "qa_id": 42,
      "question": "ETC扣费异常如何处理",
      "answer": "核实扣费记录，确认重复扣费后3个工作日退款至原账户...",
      "category_l1": "售后业务",
      "category_l2": "ETC扣费",
      "internal_process": "核实扣费记录→确认重复→发起退款",
      "feedback_dept": "财务组",
      "score": 0.9521
    }
  ],
  "total_candidates": 3,
  "work_order_id": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| query | string | 原始问题 |
| standardized_query | string | 标准化后的问题 |
| confidence | string | 置信度：high/mid/low/none |
| candidates | array | 候选答案列表，按分数降序 |
| total_candidates | int | 候选数量 |
| work_order_id | string\|null | 低置信度时自动创建的工单ID |

**confidence 含义：**

| 级别 | 分数范围 | 返回数量 | 是否创建工单 |
|------|---------|---------|------------|
| high | >=0.8 | Top-3 | 否 |
| mid | 0.5~0.8 | Top-5 | 否 |
| low | 0.2~0.5 | Top-10 | 是 |
| none | <0.2 | 空 | 是 |

---

## 2. 添加知识

### POST /add

手动添加一条知识到知识库。

**请求体：**

```json
{
  "question": "ETC设备不亮怎么处理",
  "answer": "检查设备是否有电，如无电则更换设备",
  "category_l1": "售后业务",
  "category_l2": "设备异常",
  "internal_process": "检查电量→申请更换",
  "feedback_dept": "设备组"
}
```

**响应体：**

```json
{
  "qa_id": 432,
  "message": "添加成功，索引已更新"
}
```

---

## 3. 工单预处理

### POST /agent/process

对工单数据执行入库预处理流水线（清洗→规整+分类→HyDE改写）。

**请求体：**

```json
{
  "question": "客户张三（电话：13800138000）反馈：ETC重复扣费了",
  "answer": "核实扣费记录，确认重复扣费后退款",
  "context": "工单类型=通行异常/多扣费，流转至=财务组",
  "user_id": "agent_001"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question | string | 是 | 工单问题描述（含客户信息前缀） |
| answer | string | 否 | 处理结果/备注 |
| context | string | 否 | 工单额外上下文（工单类型、流转至等） |
| user_id | string | 否 | 操作人ID |

**响应体：**

```json
{
  "question": "ETC重复扣费如何处理",
  "answer": "核实扣费记录，确认重复扣费后3个工作日退款至原账户",
  "internal_process": "核实扣费记录→确认重复→发起退款",
  "feedback_dept": "财务组",
  "is_duplicate": false,
  "duplicate_of": null,
  "similarity_score": 0.0,
  "category_l1": "售后业务",
  "category_l2": "ETC扣费",
  "category_confidence": 0.0,
  "needs_review": false,
  "review_highlights": [],
  "current_step": "hyde_rewrite",
  "error": null
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| needs_review | bool | 是否需要人工审核 |
| review_highlights | array[string] | 审核要点（如"改写丢失关键词['逾期']"） |
| is_duplicate | bool | 是否与已有知识重复 |
| current_step | string | 当前执行到的步骤 |

---

## 4. 知识软删除/恢复

### PUT /qa/status

将知识标记为 active/deprecated/archived，检索时自动过滤非 active 记录。

**请求体：**

```json
{
  "qa_id": 42,
  "status": "deprecated"
}
```

| status | 说明 |
|--------|------|
| active | 正常使用，参与检索 |
| deprecated | 已过时，不参与检索，可恢复 |
| archived | 已归档，不参与检索 |

**响应体：**

```json
{
  "qa_id": 42,
  "status": "deprecated",
  "message": "状态已更新为deprecated"
}
```

---

## 5. 业务配置管理

### GET /config/{key}

获取业务配置值（关键词列表、正则规则等）。

**示例：**

```
GET /api/v1/config/brand_keywords
```

**响应：**

```json
{
  "key": "brand_keywords",
  "value": ["ETC", "etc", "速通", "解悠", "千方", "满帮", "普惠", "宝付", "狮桥", "9901", "1101"]
}
```

### PUT /config/{key}

热更新业务配置，自动刷新缓存，无需重启服务。

**请求体：**

```json
{
  "value": ["ETC", "etc", "速通", "解悠", "千方", "满帮", "普惠", "宝付", "狮桥", "9901", "1101", "新品牌"],
  "description": "品牌名列表"
}
```

**响应：**

```json
{
  "key": "brand_keywords",
  "message": "配置已更新，缓存已刷新"
}
```

### POST /config/reload

强制刷新所有配置缓存（从DB重新加载）。

**响应：**

```json
{
  "message": "所有配置缓存已刷新，将从DB重新加载"
}
```

**可配置的 key 列表：**

| key | 类型 | 说明 |
|-----|------|------|
| forbidden_new_kws | string[] | 幻觉检测关键词列表 |
| must_preserve_kws | string[] | 必须保留关键词列表 |
| brand_keywords | string[] | 品牌名列表 |
| subject_keywords | string[] | 业务主体关键词列表 |
| question_words | string[] | 疑问词列表 |
| preserve_question_words | string[] | 必须保留疑问词列表 |
| filler_patterns | string[] | 口语填充词正则列表 |
| core_patterns | object[] | 同义替换规则列表 [{pattern, replacement}] |
| clean_rules | string[] | 业务清洗正则列表 |
| qa_statuses | string[] | 合法知识状态枚举 |

---

## 6. 健康检查

### GET /health

**响应：**

```json
{
  "status": "ok"
}
```