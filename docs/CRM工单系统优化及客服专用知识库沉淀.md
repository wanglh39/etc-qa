
客服工单流转系统优化—挑战杯技术文稿


# 一、项目概述


## 1.1项目背景


传统企业客服工单处理模式存在重复咨询量大、工单流转链路长、部门处理冗余、人工成本高、问题响应时效慢等核心痛点。海量标准化、重复性的用户咨询问题，仍需通过CRM系统发起工单、跨部门流转处理，占用客服及业务部门大量人力，导致简单问题处理效率极低；同时新增、个性化问题缺乏标准化沉淀机制，历史优质解决方案无法复用，长期造成客服服务质量参差不齐、用户等待时长过长、企业运维成本居高不下。


为解决以上行业痛点，本系统基于微调语音识别模型+RAG+Agent数据处理，对传统CRM工单体系进行智能化升级，实现语音问题智能提炼、分层自动化处理，缩短服务响应周期、沉淀企业专属客服知识库。


## 1.2产品定位


本产品是嵌入企业现有CRM工单系统的智能客服问题处理辅助系统，不替代原有CRM工单流转体系，而是做前置语音识别、问题智能提炼、智能分流与知识沉淀优化。


针对高频重复问：通过微调语音模型总结标准化问题，无需创建工单、无需人工介入，通过RAG知识库直接输出历史最优解决方案，经人工审核，秒级响应用户。


针对新增/非重复复杂问题：语音提炼后的标准化问题，通过Agent完成数据去重、文本清洗、语义规整，经人工审核后周期性入库迭代，持续扩充知识库，逐步降低重复工单量。


最终实现「问题智能提炼、重复问题智能化秒回、复杂问题标准化流转、服务知识常态化沉淀」的闭环体系。


## 1.3核心价值


| 价值维度 | 说明 |
| --- | --- |
| 语音识别能力 | 专属微调模型适配客服行业黑话、专业术语、口语化表达，实现语音→标准化问题的智能提炼 |
| 效率提升 | 高频重复咨询无需工单流转，客服响应效率提升 |
| 成本降低 | 大幅减少人工客服基础答疑、语音转写工单描述、问题梳理工作量，降低各业务部门工单处理冗余成本 |
| 服务标准化 | 统一语音提炼话术、复用历史最优解决方案，规避人工解答差异，提升用户服务体验 |
| 知识自迭代 | 通过Agent+人工审核机制，自动规整新增问题，持续扩充优化企业客服知识库 |
| 兼容原有体系 | 无缝对接现有CRM系统，不改变企业原有工单流转、部门协作流程 |


## 1.4技术栈


| 层级 | 技术选型 | 说明 |
| --- | --- | --- |
| 后端框架 | FastAPI + Uvicorn | 高性能异步Python Web框架 |
| 向量数据库 | Milvus Lite | 轻量级本地向量存储，1024维余弦相似度 |
| 关系数据库 | MySQL 8.x | 结构化数据存储 |
| Embedding模型 | bge-large-zh-v1.5 | 中文语义向量编码，1024维 |
| Reranker模型 | bge-reranker-large | CrossEncoder精排，提升Top1准确率 |
| LLM | DeepSeek API | 问题规整、分类、提问改写 |
| Agent框架 | LangGraph | 状态图编排，支持条件分支 |
| 关键词召回 | rank_bm25 | BM25算法补充语义召回不足 |
| 语音识别 | FunASR（微调） | 中文语音转文字，支持领域纠错 |
| 可观测性 | LangSmith | 全链路追踪+RAG评估 |
| 部署 | Docker Compose | MySQL容器+应用容器一键编排 |


# 二、系统架构设计


## 2.1整体架构


系统采用前后端分离架构，后端基于FastAPI构建REST API，前端基于Vue3通过HTTP接口交互。系统嵌入企业现有CRM体系，不改变原有工单流转流程，而是在前端增加智能检索入口、在后端增加语音识别+Agent预处理+RAG检索能力。


## 2.2数据存储策略


采用MySQL+Milvus双库协同架构：


MySQL：存储完整QA记录（问题、答案、分类、内部流程、反馈部门、状态等），同时存储业务配置（关键词、正则规则）和提示词模板


Milvus：仅存储问题向量（1024维），用于语义检索


关联方式：通过qa_id字段关联，MySQL为主、Milvus为辅


设计优势：


1.答案文本较长，存向量库浪费空间且无法全文检索


2.问题较短，向量化后语义匹配效果好


3.检索时"问题匹配问题"，语义对齐更准确


4.答案变更不影响向量索引，只需更新MySQL



## 2.3前端核心组件与状态管理


**阶段概述**


开发阶段是将设计蓝图转化为可运行代码的核心过程。团队基于Vue3 + Composition API + TS技术栈，采用模块化开发策略。核心组件的开发是重中之重，包括基于Web Audio + RecordRTC封装的AudioRecorder录音组件、支持流式渲染的RAG结果面板、对接QueryRewrite与批量入库的知识库管理表格、基于ECharts 5.x的数据看板以及对接三层配置中心的系统表单。在状态管理方面，团队利用Pinia构建了模块化的Store，将用户信息、权限、音频状态、RAG上下文等独立管理。同时，完成了Axios请求的深度封装以及自定义权限指令v-permission的开发，为整个系统提供了统一的底层支撑。


**修复 BUG**


在前端组件开发过程中，团队借助AI编程助手快速定位并修复语法缺陷。以SmartWorkbench.vue样式修复为例，AI通过逐行扫描`<style>`内部CSS，定位到.content-block的margin-bottom缺少分号的语法缺陷，并自动生成修复方案

修复后的数据看板ECharts渲染效果如下：

![数据看板—ECharts组件渲染](images/admin_dashboard.png)


## 2.4前端路由与权限机制


**设计理念**


为了解决传统全量路由方案的安全隐患与性能问题，将路由权限交由后端控制，前端仅作为渲染载体，杜绝了前端硬编码权限被绕过的风险。懒加载与路由缓存的结合做到在保障安全的前提下，兼顾了AI工作台对响应速度的极致要求。动态菜单与路由的绑定极大降低了权限变更的维护成本。

登录页作为路由守卫入口如下：

![登录页—路由守卫入口](images/login_page.png)


**路由表结构设计**


客服工单流转系统的路由表采用了"静态路由+动态路由"的混合架构。静态路由仅包含登录页、403页、404页等无需权限的基础页面；动态路由则根据用户角色从后端获取，包含智能问答、知识库管理、人工审核、数据看板、系统配置五大业务模块。所有业务路由均采用懒加载策略，通过()=>import()语法实现按需加载，显著降低了首屏加载时间。路由元信息meta中设计了permission字段，用于存储该路由所需的角色标识，同时增加了title、icon、hidden等字段，为动态菜单渲染和页面标题设置提供数据支撑。


**全局守卫实现**


系统通过Vue Router 4的全局前置守卫beforeEach实现了完整的权限校验链路。首先进行登录态校验，若未登录且目标非白名单页面，则重定向至登录页；若已登录但用户信息未获取，则触发用户信息与动态路由的拉取，并使用router.addRoute动态注入路由；若已登录且路由已加载，则进行权限拦截，比对当前用户角色与目标路由meta.permission，无权限时跳转至403页面。同时，团队在守卫中集成了路由缓存策略，对于频繁切换的智能问答工作台，通过keep-alive配合路由meta中的keepAlive标识，保留了组件状态与RAG会话上下文，避免了重复初始化。


**路由守卫权限校验流程**


完整的权限校验流程为：用户登录成功→获取Token→路由守卫拦截→检查用户信息是否存在→不存在则请求用户信息与动态路由→动态路由注入→放行至目标页面→权限比对→无权限跳转403。这一流程确保了每次路由跳转都经过严格的安全校验，同时通过异步路由加载避免了页面闪烁。


**动态菜单渲染**


侧边导航菜单完全由动态路由驱动。MainLayout组件通过监听Pinia中的permissionRoutes状态，递归渲染菜单项。菜单的层级结构、图标、标题均从路由meta中提取，实现了路由与菜单的单一数据源。当用户角色切换或权限变更时，只需更新Store中的路由数据，菜单便会自动响应式更新，无需手动操作DOM。

超管相关功能界面如下，包括模拟登录、角色管理与账号管理：

![模拟登录—角色菜单切换](images/superadmin_impersonate.png)

![角色管理—5角色RBAC](images/superadmin_role.png)

![账号管理—用户与角色绑定](images/superadmin_account.png)


# 三、核心业务流程与功能实现


## 3.1整体业务闭环


系统的核心业务流程形成完整闭环：

![业务闭环演示1](images/demo5_full_1.png)

![业务闭环演示2](images/demo5_full_2.png)


## 3.2语音识别模块（ASR）


系统集成了微调语音识别模型，支持客服语音输入，实现"语音→文字→检索"的端到端能力。


**模型选型与微调：**


**基座模型：**FunASR-Nano-2512，中文语音识别


**微调策略：**在客服领域数据上微调，适配行业黑话、专业术语、口语化表达


**领域纠错表：**针对行业专有名词的识别纠错（如“一体机”→“ETC”“欧比优”→“OBU”“蓝呀”→“蓝牙”等），配置在config/asr.yaml，支持DB动态覆盖，不同企业部署时只需替换纠错表


**API 设计：**


POST/asr：上传音频→识别→纠错→返回文本


GET/asr/health：ASR模型加载状态检查


识别结果自动送入/query链路，实现语音→检索的端到端体验


**测试验证：**


20条真实客服问题音频测试，全部正确识别，CER（字符错误率）接近0。


**运行效果：**

![客服工作台—语音识别](images/service_workbench_recording.png)

![ASR端到端演示](images/demo4_asr_1.png)


## 3.3Agent标准化预处理


客服输入的原始问题往往包含口语化表达、填充词、客户隐私信息等噪声，直接用于检索会大幅降低匹配准确率。系统通过两步Agent预处理将问题标准化。


**第一步：clean_text（防御性清洗）**


合并多余空格


重复标点归一（"？？？"→"？"）


数字分隔符修正


客户隐私信息清洗（去除"客户张三（电话：138xxx）反馈："等前缀）


业务特定清洗规则（从config_center动态加载，不同企业可配置不同规则）


**第二步：standardize_query（智能规整）**


采用"规则优先+LLM兜底"的分层漏斗策略：


规则清洗（0 token，不调LLM）：


去除口语填充词（"我想问一下""麻烦问下""你好"等，正则匹配，规则可配置）


同义替换（"怎么办理"→"如何办理""咋整"→"如何处理"等，配置化规则表）


品牌词/疑问词保留检测


LLM评判（规则无法判定时才调LLM）：


当问题长度>30字或规则无法判断是否需要改写时，调用LLM


LLM 输出结构化结果 StandardizeOutput（need_rewrite + reason + rewritten + rewrite_confidence）


改写置信度<0.5时拒绝改写，回退为规则清洗结果


幻觉检测：改写不得引入原文未提及的业务概念（forbidden_new_kws列表校验）


关键词保留校验：must_preserve_kws中的词在原文出现时改写必须保留


**设计亮点：**规则清洗覆盖80%的常见问题，节省LLM调用成本；LLM仅在边界情况下介入，兼顾效率和质量。分层漏斗架构确保简单问题零 token处理，复杂问题有LLM兜底。


**运行效果：**

![客服工作台—标准化处理](images/service_workbench_empty.png)

![Agent预处理演示1](images/demo1_agent_1.png)

![Agent预处理演示2](images/demo1_agent_2.png)



**LangSmith 工作流追踪：**

![LangSmith—clean节点详情](images/langsmith_agent_detail_clean.png)

![LangSmith—standardize节点详情](images/langsmith_agent_detail_standarderize.png)


## 3.4RAG智能检索引擎


标准化后的问题进入RAG检索引擎，采用"双路召回+RRF融合+Reranker精排"的三级检索架构：


**第一级：双路并行召回**


向量召回（Milvus）：用bge-large-zh-v1.5将标准化问题编码为1024维向量，在Milvus中做余弦相似度检索，返回Top10候选。查询时加QUERY_PREFIX提升检索效果。自动过滤is_QueryRewrite=false（只查原始问题向量）和active_qa_ids（排除软删除记录）。


BM25召回（jieba+rank_bm25）：对标准化问题做jieba分词，用BM25Okapi算法做关键词匹配，返回Top10候选。BM25索引在服务启动时从MySQL构建，仅索引status=active的记录。BM25弥补向量检索在专有名词、缩写等场景下的不足。


**第二级：RRF 融合**


两路召回结果通过Reciprocal Rank Fusion（RRF，k=60）合并为统一候选池，去重后保留所有来源的候选。RRF的优势是不依赖绝对分数，只依赖排名，对两路召回的分数尺度差异具有天然鲁棒性。


**第三级：Reranker 精排**


用bge-reranker-large（CrossEncoder模型）对候选池做精排，将"问题候选问题"对输入模型，输出相关性分数，按分数降序重排。Reranker能捕捉语义细微差异，显著提升Top1准确率。


**Reranker 加速 + GPU 兼容性问题解决**


**第 1 轮**：分析性能瓶颈


**第 2 轮**：解决GPU兼容性问题


**评估数据（基于 ETC 客服领域 50 条测试集）：**


| 配置 | R@1 | R@3 | R@5 | MRR |
| --- | --- | --- | --- | --- |
| 仅向量召回 | 58% | 78% | 85% | 0.68 |
| +BM25双路召回 | 65% | 85% | 90% | 0.75 |
| +Reranker精排 | 73% | 90% | 95% | 0.82 |
| +QueryRewrite增强 | 89% | 95% | 98% | 0.92 |


**运行效果：**

![客服工作台—RAG检索结果](images/service_workbench_result.png)

![RAG检索演示1](images/demo2_rag_1.png)

![RAG检索演示2](images/demo2_rag_2.png)



**LangSmith 召回详情：**

![LangSmith—召回详情总览](images/langsmith_recall_detail.png)

![LangSmith—向量召回详情](images/langsmith_recall_detail_vector.png)

![LangSmith—BM25召回详情](images/langsmith_recall_detail_bm25.png)


实现补充


第1轮：描述需求，AI理解并生成代码


第2轮：细化需求，AI优化实现


## 3.5阈值判定系统


Reranker精排后，系统需要判断检索结果的可信程度，决定返回给客服的展示方式。采用差值模式（gap）而非绝对分数模式：


差值 = Top1 分数 − Top2 分数：差值大说明 Top1 显著优于其他候选，可信度高


**双条件判定：**差值 >= gap_X AND Top1 >= floor_X，防止"两个都很差但差值大"的误判


| 置信度 | 差值条件 | 底线条件 | 返回数量 | 展示建议 |
| --- | --- | --- | --- | --- |
| high | >=0.15 | Top1>=0.5 | Top3 | 简单看看 |
| mid | >=0.08 | Top1>=0.3 | Top5 | 需认真看 |
| low | >=0.03 | Top1>=0.15 | Top10 | 需认真看 |
| none | 不满足以上 |  | Top10 | 无匹配 |


**设计考量：**Reranker的绝对分数受问题长度、领域等因素影响波动大，不能作为可靠置信度。差值模式关注"Top1是否显著优于其他"，更稳定可靠。所有结果都返回给客服，置信度只影响展示优先级，不阻断服务。


## 3.6QueryRewrite增强检索


QueryRewrite是提升检索效果的关键技术：对知识库中的每条QA，LLM生成多种用户可能问的口语化问题进行改写。


**条件改写优化：**不是所有QA都需要QueryRewrite改写。系统采用两层判断：


第1层规则预判（0 token）：问题5-15 字+含品牌词+含疑问词→判定"不需要改写"，直接跳过


第 2 层 LLM 判断：规则无法判定时，调 LLM 输出 QueryRewriteJudgeOutput（need_rewrite + reason）


这一优化能跳过约80%的标准问题，大幅节省LLM调用成本。


## 3.7入库预处理流程（/api/v1/agent/process）


当新问题通过工单系统处理后，需要将处理结果标准化入库。系统通过3步Agent流水线自动完成：


**第一步：clean_text（防御性清洗）**


与检索链路相同，去除工单中的隐私信息、格式噪声等。


**第二步：structure_ingest（结构化规整 + 分类）**


这是入库链路的核心步骤，一次LLM调用完成多项任务：


问题改写：将工单描述（如"客户张三反馈重复扣费了"）改写为标准问题格式（"重复扣费如何处理"），提问式


答案结构化：将自由文本分离为 answer（面向客户话术）+ internal_process（内部操作步骤）+ feedback_dept（反馈部门）


分类匹配：从知识库分类体系（MySQL动态加载）中选择category_l1/category_l2


分类置信度：输出category_confidence（0.0~1.0），低于阈值触发needs_review人工审核


输出为PydanticSchema（StructureIngestOutput），字段自动校验，保证与数据库字段对齐。


**第三步：QueryRewrite_rewrite（条件改写）**


与检索链路的QueryRewrite相同，判断是否需要生成假设性问题。不需要改写的直接跳过。


**后处理校验：**


幻觉检测：改写不得引入forbidden_new_kws中的业务概念


关键词保留：must_preserve_kws中的词在原文出现时改写必须保留


校验失败时自动回退为原始文本，标记需人工审核


**运行效果：**

![入库结构化演示](images/demo3_ingest_1.png)

![审核历史—入库审核闭环](images/admin_audit_history.png)



## 3.8工单闭环流程


系统与CRM工单系统对接，形成完整闭环：


1.客服提问→RAG未命中→提交工单系统（调外部CRM API）


2.本地work_orders表存记录（status=submitted）


3.工单系统处理（外部CRM系统，本系统不干预）


4.定时拉取已处理工单（调外部API），更新本地记录（status=answered）


5. Agent 预处理：clean_text → structure_ingest → QueryRewrite_rewrite


6.更新本地记录（status=processed）


7.周批量去重（两轮）：


第一轮：新问题vs已有知识库（RAG检索）


第二轮：新问题之间互相比对（numpy余弦相似度）


问题相似+答案相似→真重复；问题相似+答案不同→不去重


8.去重后入库（status=imported/rejected）


9.双库写入（MySQL+Milvus+BM25索引重建）+一致性校验

工单闭环涉及的前端页面如下，客服可新建CRM工单，部门处理员在列表中接收并处理：

![新建CRM工单](images/service_crm_create.png)

![部门工单处理列表](images/dept_workorder_list.png)


## 3.9知识全生命周期管理


**入库流程：**


1.数据清洗（clean_text）→结构化规整（structure_ingest）→QueryRewrite改写（QueryRewrite_rewrite）


2.周批量去重（两轮：新vs库+新vs新）


3.双库写入（MySQL+Milvus+BM25索引重建）


4.一致性校验（MySQL qa_id ↔ Milvus qa_id）


**检索过滤：**


软删除机制：qa_pairs.status字段（active/deprecated/archived）


检索时自动过滤status!=active的记录


Milvus向量不物理删除，通过active_qa_ids列表过滤


**定期维护：**


每周：工单去重（weekly_dedup.py）


每月：RAG评估（eval_rag.py）+QueryRewrite全量更新


每季度：知识库审计

知识全生命周期管理相关界面如下，管理员通过知识库管理页面维护全生命周期，运维通过定时任务调度执行周期性维护：

![知识库管理—全生命周期](images/admin_knowledge_list.png)

![定时任务调度—周期维护](images/ops_scheduler.png)


## 3.10可观测性


**LangSmith 全链路追踪：**


@traceable装饰器标注关键函数（RecallEngine.recall/vector_recall/bm25_recall/Reranker.rerank）


LangGraph + ChatOpenAI 自动追踪（无需额外代码）


LangSmith未安装时自动降级为noop，不影响功能


**RAG 评估：**


eval_rag.py：4 配置消融对比（baseline / +BM25 / +Reranker / +QueryRewrite），输出 R@1/R@3/R@5/R@10/MRR + 失败 case 分析


eval_langsmith.py：LangSmith evaluate API，3个评估器，无LangSmith时自动降级本地跑


eval_structure_ingest.py：入库改写质量评估（语义保持+格式规范+分类一致性+答案结构化质量）

可观测性相关界面如下，运维可查看系统状态总览与异常告警，超管可追溯操作日志：

![系统状态总览](images/ops_status.png)

![异常告警](images/ops_alert.png)

![操作日志—审计追踪](images/superadmin_operation_log.png)



# 四、关键技术决策与实现细节


## 4.1提示词模板化+结构化输出


**问题：**提示词写死在代码里，改一个字都要改代码重新部署；LLM返回纯文本JSON，手动解析容易出错。


## 4.2分层漏斗架构


Agent预处理采用"规则优先+LLM兜底"的分层漏斗：


这种设计在保证质量的同时大幅降低LLM调用成本，尤其适合客服场景中大量标准化问题的处理。


## 4.3模型能力注册表


不同LLM对结构化输出的支持能力不同，系统通过模型能力注册表（models.yaml llm_registry）自动适配：


优先级：agent.yaml 显式指定 > 注册表 > 代码兜底(none)。切换模型时自动适配最佳结构化输出方式，业务代码无需修改。


## 4.4领域适配设计


系统设计时充分考虑不同企业/领域的适配需求：


| 纠错表可配置 | ASR纠错表存YAML+DB，不同领域只需替换纠错条目 |
| --- | --- |
| 关键词列表可配置 | 品牌词、业务词、疑问词等全部存DB，API热更新 |
| 分类体系动态加载 | 从MySQL qa_pairs表自动提取分类树，新增分类无需改代码 |
| 提示词模板化 | PromptEngine从DB加载模板，不同领域可定制不同提示词 |
| 清洗规则可配置 | filler_patterns、core_patterns、clean_rules全部配置化 |

分类管理页面实现了分类体系的动态加载，新增分类无需改代码：

![分类管理—分类体系动态加载](images/admin_category.png)


## 4.5核心代码设计展示


### 4.5.1分层漏斗架构—规则清洗（clean_text.py）


规则清洗零 token处理：从DB加载正则规则，去除隐私信息/填充词/格式噪声，覆盖80%常见问题。

![AI辅助—clean_text实现](images/ai_interact_s1_1_1.png)


### 4.5.2三级检索架构—RRF融合（recall.py）


向量召回+BM25召回并行执行，RRF（k=60）按排名融合，不依赖绝对分数，对两路分数尺度差异天然鲁棒。


**RRF 融合方案讨论**

![AI辅助—RRF方案讨论1](images/ai_interact_s4_1_1.png)

![AI辅助—RRF方案讨论2](images/ai_interact_s4_1_2.png)


### 4.5.3QueryRewrite 条件改写—规则预判跳过（rewrite.py）


问题 5-15 字 + 含品牌词 + 含疑问词 → 直接跳过，0 token。仅边界情况调 LLM，跳过约 80% 的标准问题。

![AI辅助—rewrite条件改写](images/ai_interact_s2_1_1.png)


### 4.5.4阈值差值判定（threshold.py）


差值 = Top1 分数 − Top2 分数，双条件判定（差值 ≥ gap AND Top1 ≥ floor），防止"两个都很差但差值大"的误判。

![AI辅助—阈值判定实现](images/ai_interact_s3_1_1.png)


### 4.5.5AgentState状态流转（state.py）


Pydantic BaseModel定义全状态，LangGraph节点间通过AgentState传递，字段自动校验+类型安全。

![AI辅助—AgentState定义](images/ai_interact_s3_2_1.png)


### 4.5.6配置中心三级降级（config_center.py）


DB→缓存→YAML三级降级：DB修改后60秒自动生效，DB不可用时降级到YAML，保证服务不中断。

![配置管理—三层配置中心](images/admin_config.png)


## 4.6前端交互优化与防抖策略


### 4.6.1文本输入防抖


在智能问答工作台的搜索框中，团队实现了500ms的输入防抖。用户停止输入500ms后，才会触发RAG检索请求，避免了每敲击一个字符就发送一次请求的资源浪费。同时，结合Pinia本地缓存，对相同问题的检索结果进行缓存，当用户删除后重新输入相同问题时，直接从缓存中读取结果，实现了“零延迟”的重复查询体验。


### 4.6.2按钮防重复点击


针对提交工单、保存配置、知识库入库等关键操作按钮，团队封装了v-loading防重复点击指令。该指令在按钮点击后立即禁用按钮并显示加载状态，直到异步操作完成或超时后才恢复。这有效防止了客服因网络延迟或操作习惯导致的多次点击，避免了工单重复创建、配置重复保存等数据一致性问题。


### 4.6.3录音组件防抖


AudioRecorder录音组件的启停按钮进行了专门的防抖处理。由于录音涉及浏览器硬件权限与音频流初始化，快速连续点击极易导致状态混乱或录音文件损坏。团队通过状态机加300ms防抖的组合策略，确保录音的启动与停止操作有足够的时间完成状态切换，保障了录音功能的稳定性。


### 4.6.4请求级防抖


在Axios拦截器层面，团队实现了请求级的防抖与取消机制。通过生成请求的唯一标识（URL+参数哈希），在发送新请求前检查是否存在相同标识的未完成请求，若存在则主动取消旧请求。这一机制在RAG检索场景中尤为重要，当客服连续修改问题时，只有最后一次修改的请求会被保留，之前的请求均被自动取消，既节省了带宽，又避免了旧结果覆盖新结果的竞态问题。


### 4.6.5设计心得


防抖与防重复点是系统性能与用户体验的关键保障。在AI交互场景中，用户的操作节奏与传统表单系统截然不同，他们可能会在思考时频繁修改输入，或在等待AI回答时焦虑地重复点击。多层次的防抖策略协同工作：输入防抖减少了无效请求，请求级防抖避免了竞态问题，按钮防抖保障了数据一致性，录音防抖确保了硬件交互的稳定性。


# 五、测试体系


## 5.1测试策略


系统采用三层测试体系，确保从单元到集成的全面覆盖：


| 测试层级 | 数量 | 覆盖率 | 说明 |
| --- | --- | --- | --- |
| 单元测试 | 464 passed | 96% | Mock外部依赖，可离线运行 |
| 集成测试 | 242 passed | 85% | 连接真实MySQL/Milvus/LLM |
| E2E测试 | 20+ passed |  | FastAPI TestClient全端点覆盖 |


**测试运行结果：**

![单元测试结果](images/test_unit.png)

![集成测试结果](images/test_integration.png)


## 5.2单元测试


目录结构：测试目录镜像源码目录（tests/agent/→agent/，tests/rag/→rag/）


Mock策略：MockMySQL、Milvus、LLM等外部依赖，测试不依赖真实服务


覆盖率：96%，通过pytest-cov + --cov-fail-under=80强制门禁


关键测试：


Agent processors：规则清洗+LLM评判+幻觉检测+关键词保留


RAG：双路召回+RRF合并+Reranker+阈值判定（gap/absolute两种模式）


配置中心：DB优先→YAML兜底→缓存TTL→线程安全


提示词引擎：jinja2渲染+DB加载+缓存失效


## 5.3集成测试


真实环境：连接真实MySQL、Milvus Lite、Embedding模型、Reranker模型


session级fixture复用：MySQL连接、Milvus连接、模型加载等只初始化一次


环境隔离：测试库etc_qa_test与开发库etc_qa完全隔离


ASR 隔离：FunASR 模型加载在 Windows 多线程环境下会 crash，用 subprocess 隔离运行


关键测试：


L1-L4 基础集成：MySQL CRUD + Milvus 向量操作 + RAG 全链路


Agent 处理器集成：LLM 真实调用 + 结构化输出 + 降级


提示词集成：版本管理 + 影子测试 + API 端到端


覆盖率补充：mysql_client error handling(22个)、milvus_client gRPC error(5个)、config_center边界(4个)等


## 5.4评估脚本


| 脚本 | 评估内容 | 关键指标 |
| --- | --- | --- |
| eval_rag.py | RAG检索质量，4配置消融对比 | R@1,R@3,R@5,R@10,MRR |
| eval_asr.py | ASR端到端（TTS→识别→纠错→RAG） | CER,纠错后CER,R@1 |
| eval_structure_ingest.py | 入库改写质量 | 语义保持,分类一致性,格式规范度 |
| eval_prompt_diff.py | 提示词版本对比 | 通过率,回退用例,改善用例 |
| eval_langsmith.py | LangSmith平台评估 | R@1,R@3,MRR |


## 5.5前端测试


**阶段概述**


测试阶段是保障系统质量的最后一道防线。团队构建了多层次的测试体系：单元测试方面，使用Vitest对文本清洗、音频格式转换等纯工具函数进行了全覆盖测试；功能测试方面，重点验证了录音上传的完整性、RAG检索的准确性、知识库入库审核的流程闭环以及数据看板图表的渲染正确性；边界场景测试方面，模拟了网络超时重试、越权访问拦截、高并发请求等极端情况，确保系统在异常状态下不会崩溃且能给出友好的错误提示。


**代码测试**


# 六、Docker容器化部署


## 6.1容器化策略


系统采用Docker Compose编排，实现一键部署：


| 组件 | 容器化方式 | 说明 |
| --- | --- | --- |
| MySQL | Docker容器 | 官方mysql:8.0镜像，数据持久化到Docker Volume |
| 应用 | Docker容器 | 自定义镜像（Dockerfile），包含Python+依赖 |
| Milvus | Lite模式 | .db文件存储在Docker Volume，代码零改动 |
| 模型文件 | Volume挂载 | 太大（~10GB）不打进镜像，从宿主机挂载 |
| API Key | .env文件 | 不进镜像，防泄露 |


## 6.2开发环境


**docker-compose.dev.yml 提供开发专用编排：**


MySQL容器自动建库建表


应用容器挂载源码目录，支持reload热更新


模型文件只读挂载（:ro），防止容器内意外修改


**开发实践记录（模型文件路径 / 配置路径问题的排查过程）**


第1轮：报Bug，AI定位根因并修复


第2轮：追问确认，AI检查所有相关文件


## 6.3一键搭建脚本


setup.bat/setup.sh：一键完成依赖安装→模型下载→MySQL启动→数据库初始化


scripts/setup/download_models.py：从ModelScope自动下载3个模型，支持断点续传、部分下载


.env.template：环境变量模板，不含真实Key


# 七、项目成果与数据


## 7.1核心指标


| 指标 | 数值 | 说明 |
| --- | --- | --- |
| Recall@1 | 89% | 加入QueryRewrite后的检索准确率（基线73%，+16%） |
| Recall@3 | 95% | Top3召回率 |
| MRR | 0.92 | 平均倒数排名 |
| 单元测试 | 464 passed,96%覆盖率 | 全部通过 |
| 集成测试 | 242 passed,84%覆盖率 | 全部通过 |
| ASR识别准确率 | 100% | 20条领域问题音频测试 |
| QueryRewrite跳过率 | ~80% | 条件改写节省的LLM调用 |


**LangSmith 全链路追踪：**

![LangSmith—全链路总览](images/langsmith_overview.png)

![LangSmith—DeepSeek API调用详情](images/langsmith_deepseek_api_detail.png)


## 7.2检索效果消融实验


| 配置 | R@1 | R@3 | R@5 | MRR |
| --- | --- | --- | --- | --- |
| 仅向量召回 | 58% | 78% | 85% | 0.68 |
| +BM25双路召回 | 65% | 85% | 90% | 0.75 |
| +Reranker精排 | 73% | 90% | 95% | 0.82 |
| +QueryRewrite增强 | 89% | 95% | 98% | 0.92 |


## 7.3代码规模


| 类别 | 文件数 | 代码行数 |
| --- | --- | --- |
| 核心代码 | 30+ | ~5000行 |
| 测试代码 | 25+ | ~6000行 |
| 脚本工具 | 15+ | ~2000行 |
| 配置文件 | 10+ | ~500行 |
| 文档 | 10+ | ~3000行 |
