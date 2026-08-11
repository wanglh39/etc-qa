# ETC客服QA智能检索系统

基于 Milvus 向量数据库 + MySQL + LangGraph Agent 的 ETC 客服 QA 智能检索系统。客服输入问题后，通过向量检索 + BM25 + Reranker 找到最匹配的答案话术，新问题通过 Agent 流水线标准化后入库。

## 技术栈

| 层级 | 技术 | 版本/说明 |
|------|------|----------|
| 前端 | Vue3 + Element Plus + Pinia + ECharts | 待开发 |
| 后端 | FastAPI + Uvicorn | Python 3.10 |
| 向量数据库 | Milvus Lite | 本地文件，无需 Docker |
| 关系数据库 | MySQL 8.x | :3306 |
| Embedding | bge-large-zh-v1.5 | 1024 维 |
| Reranker | bge-reranker-large | CrossEncoder |
| LLM | DeepSeek Chat | 规整/分类/HyDE |
| Agent | LangGraph | 状态图编排 |
| BM25 | jieba + rank_bm25 | 关键词召回 |
| 追踪 | LangSmith | 全链路追踪 |

## 环境要求

- Python 3.10+
- MySQL 8.x（端口 3306）
- Anaconda/Miniconda（推荐）
- 模型文件（bge-large-zh-v1.5 + bge-reranker-large，见下方路径配置）

## 快速启动

### 1. 创建 conda 环境

```bash
conda create -n etc_qa python=3.10 -y
conda activate etc_qa
```

### 2. 安装依赖

```bash
cd etc_qa
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env，填入 DeepSeek API Key
```

### 4. 初始化数据库

```bash
# 建表 + 导入知识库数据（默认 test 环境）
python scripts/data/init_db.py test

# 初始化业务配置（关键词/规则导入 MySQL）
python scripts/data/init_config.py test
```

### 5. 启动服务

```bash
# 开发环境
python main.py

# 或指定环境（Windows PowerShell）
$env:ETC_QA_ENV='test'
python main.py
```

服务启动后访问：http://localhost:8000/api/v1/health

### 6. 运行测试

```bash
python -m pytest tests/ -q
```

## 环境切换

通过环境变量 `ETC_QA_ENV` 切换：

| 环境 | 用途 | MySQL 库 | Milvus 库 |
|------|------|----------|-----------|
| dev | 日常开发 | etc_qa | milvus_etc_qa.db |
| test | 测试召回率 | etc_qa_test | milvus_etc_qa_test.db |
| prod | 生产 | etc_qa | milvus_etc_qa.db |

```bash
# Windows
$env:ETC_QA_ENV='test'

# Linux/Mac
export ETC_QA_ENV=test
```

## 模型路径配置

默认模型路径在 `config.yaml` 中配置，支持通过环境变量覆盖：

```yaml
models:
  embed:
    path: "${MODEL_BASE_DIR:C:\\Users\\wlh19\\.cache\\modelscope\\hub}\\models\\BAAI\\bge-large-zh-v1___5"
```

如果模型在其他位置，设置环境变量：

```bash
$env:MODEL_BASE_DIR='D:\models'
```

## 项目结构

详见 [目录结构.md](目录结构.md) 和 [架构图.md](架构图.md)

## 文档索引

| 文档 | 说明 |
|------|------|
| [架构图.md](架构图.md) | 系统架构、两条核心链路、配置分层、并发架构 |
| [目录结构.md](目录结构.md) | 目录结构 + 代码调用关系 + 测试对应表 |
| [API接口文档.md](API接口文档.md) | 所有 REST API 详细说明（前后端对接用） |
| [数据库设计文档.md](数据库设计文档.md) | 所有表结构 + 字段说明 |
| [开发规范.md](开发规范.md) | 代码规范、提交规范、分支规范 |
| [交接清单.md](交接清单.md) | 已完成/待开发/注意事项 |
| [高并发演进路线.md](高并发演进路线.md) | 低→中→高三阶段演进方案 |