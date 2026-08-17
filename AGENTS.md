# AGENTS.md — 项目规则与记忆

## 基本规则

1. **改代码前先问用户**，不要自作主张
2. **代码文件只写代码，不要加注释**（除非用户明确要求）
3. **必须使用简体中文回复**
4. **每次改动完成后必须询问用户是否需要git提交**，不要自动提交

---

## 开发流水线（强制）

根据改动类型选择对应流水线，每一步都不可跳过。

### 流水线A：纯后端改动（Python代码）

```
1. 影响评估（模块/测试/测评/日志/LangSmith）→ 表格呈现给用户确认
2. 写代码 + 同步补全可观测性（logger + @traceable）
3. pytest单元测试
4. 后端文档同步（目录结构.md + 架构图.md + 挑战杯技术文稿.md）
5. 询问：集成测试？测评？git提交？
```

### 流水线B：纯前端改动（Vue/TS代码）

```
1. 影响评估（页面/组件/路由/API/菜单）→ 表格呈现给用户确认
2. 写代码
3. vue-tsc类型检查（workdir=frontend/，命令：npx vue-tsc --noEmit）
4. 前端文档同步（前端技术文稿.md）
5. 询问：git提交？
```

### 流水线C：全栈改动（前后端都改）

```
1. 影响评估（后端模块 + 前端页面/组件）
2. 写代码（后端 + 前端）
3. 后端：pytest单元测试
4. 前端：vue-tsc类型检查
5. 文档同步（后端3个文档 + 前端技术文稿.md）
6. 询问：集成测试？测评？git提交？
```

### 流水线D：权限/角色改动（新增页面、改API权限、新增角色）

```
1. 影响评估
2. 写代码（后端require_role + 前端roleAuth + 路由 + 菜单）
3. pytest + vue-tsc
4. ★角色权限矩阵校验（见下方）
5. 文档同步
6. 询问：git提交？
```

### ★角色权限矩阵校验（流水线D专属）

每次涉及权限改动，必须检查**前后端权限一致性**：

| 检查项 | 后端 | 前端 | 一致性要求 |
|--------|------|------|-----------|
| API端点权限 | `require_role("admin", "superadmin")` | 调用该API的页面`roleAuth` | 前端能访问的角色的后端也必须放行 |
| 新增页面 | 无直接后端 | 路由`meta.roleAuth` + Layout菜单 | 菜单只给有权限的角色显示 |
| 新增角色 | `init_db.py`种子 + `jwt_utils.py`硬编码 | `login.vue`跳转 + `getDefaultPath` + `roleText` | 5处都要改，缺一不可 |

**前后端权限不一致的典型bug**：前端roleAuth放了ops但后端require_role没加ops → 前端能进页面但API返回403 → "权限不足"

---

## 后端规则

### 影响评估（后端）
- **受影响的模块**：哪些文件/类/函数会被波及
- **单元测试**：哪些测试类/方法需要新增或更新
- **集成测试**：哪些集成测试可能受影响
- **测评**：改动涉及哪个测评脚本，给出本地运行命令
- **日志**：改动处是否需要加logger.info/warning/error
- **LangSmith**：改动处是否需要加@traceable装饰器

### 可观测性（后端）
- **日志**：关键流程入口/出口/异常处加`logger.info/warning/error`，日志内容要能定位问题（含关键变量值）
- **LangSmith**：新增的Service层方法或关键业务函数加`@traceable(name="xxx")`，name用模块_方法命名
- 这两步和写代码同步进行，不是事后补

### 测试命令（后端）
- sandbox：`python -m pytest tests/ -x -q -o addopts="" --ignore=tests/integration`（workdir=`backend/`）
- 本地：`C:\Users\wlh19\anaconda3\envs\etc_qa\python.exe -m pytest tests/ -x -q`（workdir=`backend/`）
- sandbox有120秒超时，heavy依赖测试只能本地跑
- conftest.py已mock langsmith/langchain_core/langgraph

### 测评命令（后端）
- `eval_asr.py`：ASR识别+检索命中率（改asr/时用）
- `eval_rag.py`：RAG召回率+准确率（改rag/时用）
- `eval_structure_ingest.py`：入库结构化质量（改structure_ingest时用）
- `eval_prompt_diff.py`：提示词版本对比（改prompt/templates/*.j2时用）
- 运行：`C:\Users\wlh19\anaconda3\envs\etc_qa\python.exe scripts/eval/eval_xxx.py`（workdir=`backend/`）

---

## 前端规则

### 影响评估（前端）
- **受影响的页面**：哪些.vue文件会被波及
- **组件**：是否有公共组件需要改
- **路由**：是否需要新增/修改路由、roleAuth权限
- **API层**：是否需要新增/修改api/*.ts函数
- **菜单**：是否需要在Layout.vue中新增/修改菜单项
- **类型**：是否需要新增/修改TypeScript interface

### 类型检查（前端）
- 命令：`npx vue-tsc --noEmit`（workdir=`frontend/`）
- 无输出=通过，有错误必须修复
- 每次改前端代码后必须跑，不能跳过

### 角色权限（前端）
- 路由权限：`meta: { roleAuth: 'admin,ops' }`（逗号分隔多角色）
- superadmin可访问所有页面（路由守卫直接放行）
- 其他角色检查roleAuth逗号分隔列表是否包含当前角色
- 菜单按角色硬编码在Layout.vue中（`v-if="currentRole === 'xxx'"`）

### 文档同步（前端）
- `docs/前端目录结构.md`：前端目录结构
- `docs/前端架构图.md`：前端框架/架构图
- `docs/前端技术文稿.md`：前端技术文档
- 改了页面/组件/路由/权限时同步更新对应文档

---

## 文档同步规则

### 后端改动
- `docs/目录结构.md`：项目目录结构
- `docs/架构图.md`：框架/架构图
- `docs/挑战杯技术文稿.md`：后端技术文档
- 三个文档和写代码同步改，改完主动告知用户改了哪些

### 前端改动
- `docs/前端目录结构.md`：前端目录结构
- `docs/前端架构图.md`：前端框架/架构图
- `docs/前端技术文稿.md`：前端技术文档
- 三个文档和写代码同步改，改完主动告知用户改了哪些

### 权限改动
- 后端+前端文档都要同步
- 特别更新前端技术文稿的「角色权限体系」章节

---

## 项目信息

- **项目根目录**: `C:\Users\wlh19\Desktop\挑战杯\etc_qa\`
- **后端代码目录**: `backend/`（Python/FastAPI）
- **前端代码目录**: `frontend/`（Vue3/TypeScript）
- **Python环境**: conda环境`etc_qa`，解释器`C:\Users\wlh19\anaconda3\envs\etc_qa\python.exe`
- **技术栈**: MySQL + Milvus LITE + FastAPI + Vue3 + Element Plus + ECharts + LangGraph + LangSmith
- **用户是小白**：只懂玩具级React（前端改用Vue3），不懂Docker/Milvus/FastAPI/Reranker

### 角色体系（5角色RBAC）

| 角色 | 定位 | 默认账号 | 默认首页 |
|------|------|---------|---------|
| superadmin | 系统管理 | superadmin/123456 | /workbench/admin/account |
| ops | 运维工程师 | ops/123456 | /workbench/admin/status |
| admin | 业务管理 | admin/123456 | /workbench/admin/auditList |
| service | 客服 | service/123456 | /service |
| dept | 部门处理员 | dept/123456 | /dept/handle/{dept} |

---

## 关键架构决策

### ASR
- 伪流式模式：VAD切句 → Fun-ASR-Nano离线识别 → 回调on_final
- 启动预热+复用：warmup预加载模型，start_stream复用backend，预热失败退化为懒加载
- 流式路径必须应用纠错表（_apply_corrections）

### RAG
- 双路并行召回：ThreadPoolExecutor(max_workers=2)并行Milvus向量+BM25关键词
- RRF合并（vector_weight=0.7, bm25_weight=0.3）+ Reranker精排
- Milvus定期重连（每30次查询主动_reconnect，防gRPC too_many_pings）

### 状态机
- SessionState：IDLE → LISTENING → QUERY_READY → CANDIDATES_SHOWN → RESOLVED
- WebSocket _set_state管理状态转换+通知前端

### 可观测性
- 日志：stdout + `backend/logs/etc_qa.log`（10MB轮转，5个备份）
- LangSmith @traceable：asr_transcribe、rag_query、recall、vector_recall、bm25_recall、rerank
- 告警监控：alert/monitor.py内存滑动窗口指标采集 + 6条告警规则 + 站内告警/webhook通知

### 提示词管理
- PromptEngine加载优先级：.j2文件 > DB热修 > 代码fallback
- backend/prompt/templates/*.j2：4个模板，git管理版本

### 前端安全
- sessionStorage存储认证信息（非localStorage），关浏览器自动清除
- 路由守卫首次导航调/api/auth/verify验证token有效性
- 前后端权限双重校验：前端roleAuth + 后端require_role

---

## 已完成的重要改动

### 后端
1. corrections加"E T C"→"ETC"等字母空格纠错
2. greeting正则加"为你好""为你"
3. 流式路径加纠错表应用
4. RAG find_expected_id加模糊匹配
5. VAD换成numpy能量VAD + min_silence_ms=200
6. 双路召回并行
7. ASR模型复用+启动预热
8. 状态机（ws_state.py + websocket.py）
9. Milvus定期重连防too_many_pings
10. 日志文件+轮转
11. LangSmith @traceable
12. 提示词文件化管理（Phase 1）
13. RAG检索性能优化（LLM timeout+LRU缓存+超时降级）

### 任务1-3 + 安全 + 告警
14. 前端知识库列表页（commit af912cf）
15. 账号权限管理+超管分离+操作日志（commit cf854ab）
16. 定时任务调度服务+安全修复(localStorage→sessionStorage)+饼图修复（commit fb9c6f1）
17. 异常告警机制：指标采集+6条规则+站内告警+webhook+前端管理页（commit 6187c3f）

### 前端重构 + 运维
18. 新增ops角色（运维工程师）：init_db + jwt_utils + 路由 + 菜单
19. 运维页面：系统状态总览(status.vue) + 性能监控看板(monitor.vue)
20. 数据看板增强：KPI卡片环比+可点击跳转+时间范围选择器+工单/知识状态分布图
21. 角色体系重构：superadmin只管账号/角色/日志，ops管运维，admin管业务+内容
22. 分类管理页面挂载（category/index.vue，前后端API已ready）
23. 清理3个废弃页面（AdminWorkbench/wait/record）
24. 前端技术文稿独立文档

---

## 待完成

- 答辩材料整理
- eval_asr.py本地重跑验证
- 阶段2：Pinia状态管理 + 面包屑 + 统一错误处理 + 路由懒加载
