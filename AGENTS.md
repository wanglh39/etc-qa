# AGENTS.md — 项目规则与记忆

## 基本规则

### 代码修改规则
1. **改代码前先问用户**，不要自作主张
2. **代码文件只写代码，不要加注释**（除非用户明确要求）
3. **必须使用简体中文回复**
4. **改代码前必须做影响范围评估**，具体包括：
   - **受影响的模块**：哪些文件/类/函数会被波及
   - **单元测试**：哪些测试类/方法需要新增或更新
   - **集成测试**：哪些集成测试可能受影响
   - **测评**：改动涉及哪个测评脚本（eval_asr/eval_rag/eval_structure_ingest/eval_prompt_diff），给出本地运行命令
   - **日志**：改动处是否需要加logger.info/warning/error
   - **LangSmith**：改动处是否需要加@traceable装饰器
   - 评估结果以表格形式呈现给用户，确认后再改
5. **每次改动必须同步补全可观测性**，具体包括：
   - **日志**：关键流程入口/出口/异常处加 `logger.info/warning/error`，日志内容要能定位问题（含关键变量值）
   - **LangSmith**：新增的Service层方法或关键业务函数加 `@traceable(name="xxx")`，name用模块_方法命名（如 `rag_query`、`asr_transcribe`）
   - 这两步和写代码同步进行，不是事后补
6. **每次改动必须同步更新核心文档**，具体包括：
   - `backend/docs/目录结构.md`：项目目录结构
   - `backend/docs/架构图.md`：框架/架构图
   - `backend/docs/挑战杯技术文稿.md`：技术文档
   - 这三个文档和写代码同步改，改完主动告知用户改了哪些
   - 然后询问用户是否需要更新其余文档（API接口文档、数据库设计文档、开发规范、数据规范、交接清单、高并发演进路线、AI交互脚本、README等）
7. **每次改动完成后必须询问用户是否需要git提交**，不要自动提交

### 测试规则（强制）
1. **每次改代码后必须跑单元测试**，不能跳过
2. **单元测试不加载真实模型**（funasr.AutoModel/SentenceTransformer/MilvusClient等），用mock替代。但允许import库本身（如torch）用于patch
3. **单元测试保持镜像测试结构**：测试类对应源码类，测试方法对应源码方法
4. **单元测试通过后，询问用户是否需要跑集成测试**
5. **集成测试通过后（或用户跳过集成测试后），询问用户是否需要跑测评**，并给出对应的测评脚本路径和本地运行命令
6. sandbox测试命令：`python -m pytest tests/ -x -q -o addopts="" --ignore=tests/integration`（workdir=`backend/`，`-o addopts=""`去掉coverage避免加载所有模块）
7. 本地测试命令：`C:\Users\wlh19\anaconda3\envs\etc_qa\python.exe -m pytest tests/ -x -q`（workdir=`backend/`）
8. sandbox有120秒超时，heavy依赖（funasr/sentence_transformers/pymilvus）的测试只能在本地终端跑
9. conftest.py已mock langsmith/langchain_core/langgraph（noop traceable装饰器），避免8秒导入开销

### 测评规则（强制）
1. **测评在单元测试+集成测试之后进行**：单元测试通过→询问集成测试→集成测试通过或跳过后→询问测评
2. **每次改动必须给出测评命令**，让用户可以直接复制到本地终端运行
3. 测评脚本目录：`backend/scripts/eval/`，可用脚本：
   - `eval_asr.py`：ASR识别准确率+检索命中率评测（改asr/相关代码时用）
   - `eval_rag.py`：RAG检索召回率+准确率评测（改rag/相关代码时用）
   - `eval_structure_ingest.py`：入库结构化质量评测（改structure_ingest相关代码时用）
   - `eval_prompt_diff.py`：提示词版本before/after对比评测（改prompt/templates/*.j2时用）
   - `eval_rag_perf.py`：RAG检索性能基准测试，7步分步计时+p50/p95/p99分位统计（排查检索慢时用）
4. 测评运行命令格式：`C:\Users\wlh19\anaconda3\envs\etc_qa\python.exe scripts/eval/eval_xxx.py`（workdir=`backend/`）
5. 测评脚本需本地运行（加载真实模型+DB+Milvus），sandbox超时跑不了

## 项目信息

- **项目根目录**: `C:\Users\wlh19\Desktop\挑战杯\etc_qa\`
- **后端代码目录**: `C:\Users\wlh19\Desktop\挑战杯\etc_qa\backend\`（所有Python代码、测试、配置、文档都在此目录下）
- **前端代码目录**: `C:\Users\wlh19\Desktop\挑战杯\etc_qa\frontend\`（Vue3）
- **Python环境**: conda环境`etc_qa`（Python 3.10），解释器路径`C:\Users\wlh19\anaconda3\envs\etc_qa\python.exe`
- **技术栈**: MySQL + Milvus LITE + FastAPI + Vue3 + LangGraph + LangSmith
- **用户是小白**：只懂玩具级React（前端改用Vue3），不懂Docker/Milvus/FastAPI/Reranker

## 关键架构决策

### ASR
- 伪流式模式（PseudoStreamingBackend）：VAD切句 → Fun-ASR-Nano离线识别 → 回调on_final
- **启动预热+复用**：服务启动时warmup预加载模型（避免首通延迟10-30秒），start_stream复用backend，stop_stream不销毁；预热失败退化为懒加载兜底
- 双声道场景不需要diarizer（物理声道分离），单声道混音才需要pyannote
- 流式路径（WebSocket+伪流式）必须应用纠错表（_apply_corrections）

### RAG
- 双路并行召回：ThreadPoolExecutor(max_workers=2)并行跑Milvus向量+BM25关键词
- RRF合并（weighted_rrf: vector_weight=0.7, bm25_weight=0.3）
- Reranker精排（CrossEncoder）
- Milvus定期重连（每30次查询主动_reconnect，避免gRPC too_many_pings）

### 状态机
- SessionState枚举：IDLE → LISTENING → QUERY_READY → CANDIDATES_SHOWN → RESOLVED
- WebSocket里_set_state函数管理状态转换+通知前端
- 控制消息：select_answer（→RESOLVED）、reset（→IDLE）

### 可观测性
- 日志：stdout + `backend/logs/etc_qa.log`（10MB轮转，5个备份）
- LangSmith @traceable：asr_transcribe、rag_query、recall、vector_recall、bm25_recall、rerank

### 提示词管理
- 模板文件优先：PromptEngine加载优先级 .j2文件 > DB热修 > 代码fallback
- backend/prompt/templates/*.j2：4个模板（judge/hyde_judge/hyde/structure_ingest），git管理版本
- .j2文件含{# metadata #}头注释（prompt_key/description/variables），Jinja2渲染时自动剥离
- 调试边界：改指令文字（角色/规则/格式），不删{{变量}}占位符（代码运行时填充）
- version_manager.py仍为DB-based（Phase 2可改git-based），API路由不变

## 已完成的重要改动

1. corrections加"E T C"→"ETC"等字母空格纠错（backend/config/asr.yaml）
2. greeting正则加"为你好""为你"（backend/asr/ws_helpers.py）
3. 流式路径加纠错表应用（backend/asr/websocket.py + backend/scripts/eval/eval_asr.py）
4. RAG find_expected_id加模糊匹配 + test_questions.json加expected_qa_id手动映射
5. VAD换成numpy能量VAD + min_silence_ms=200（backend/scripts/eval/eval_asr.py）
6. 双路召回并行（backend/rag/recall.py）
7. ASR模型复用，不每次重新加载（backend/asr/streaming.py）
8. 状态机（backend/asr/ws_state.py + backend/asr/websocket.py）
9. Milvus定期重连防too_many_pings（backend/db/milvus_client.py）
10. 日志文件+轮转（backend/utils/logger.py）
11. LangSmith @traceable加到QAService.query和ASRService.transcribe
12. ASR模型启动预热（backend/asr/streaming.py warmup + backend/app.py create_service调用），避免首通用户等模型加载10-30秒
13. tests/asr/镜像整理：拆分test_ws_helpers.py+test_ws_state.py，合并test_websocket_endpoint.py到test_websocket.py
14. 提示词文件化管理（Phase 1）：提取4个.j2模板到backend/prompt/templates/，PromptEngine优先读文件>DB>代码fallback，git管理版本
15. RAG检索性能优化：LLM加timeout=10s+max_retries=1+max_tokens减至256，_standardize加500条LRU缓存+超时降级用原问题检索

## 测试覆盖

- backend/tests/asr/test_ws_helpers.py: TestIsGreeting/TestIsCorrection/TestHasPronoun/TestCharOverlapRatio/TestGetRecentAudio/TestExtractChannel/TestDoQuery/TestIdentifySpeaker/TestDoDiarizeSegment
- backend/tests/asr/test_ws_state.py: TestQueryAccumulator/TestQueryCache/TestContextWindow/TestVADSilenceDetector/TestVADFeedAudio/TestAccumulatorCheckTimeout/TestSessionState
- backend/tests/asr/test_websocket.py: WebSocket端点测试(asr_stream端到端)+TestStateMachine/TestControlMessageUpdate/TestOnFinalCorrections/TestFilterPipeline
- backend/tests/asr/test_streaming.py: test_start_stream_reuses_backend, test_stop_stream_preserves_backend, TestStreamingASRServiceWarmup
- backend/tests/asr/test_service.py: test_apply_corrections_etc_spaces等
- backend/tests/rag/test_recall.py: test_parallel_recall等
- backend/tests/agent/test_prompt_engine.py: TestPromptEngineRender/TestPromptEngineShadowAndEdgeCases/TestPromptEngineFileTemplate（文件读取+DB降级+fallback兜底）
- backend/tests/asr/与backend/asr/镜像结构一一对应

## 待完成

- 前端Vue3开发
- 答辩材料整理
- eval_asr.py本地重跑验证全部修复效果
- 集成测试更新（如需要）