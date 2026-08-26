# ETC客服QA智能检索系统

基于 Milvus 向量数据库 + MySQL + LangGraph Agent 的 ETC 客服 QA 智能检索系统。客服输入问题后，通过向量检索 + BM25 + Reranker 找到最匹配的答案话术，新问题通过 Agent 流水线标准化后入库。

## 技术栈

| 层级 | 技术 | 版本/说明 |
|------|------|----------|
| 后端 | FastAPI + Uvicorn | Python 3.10 |
| 向量数据库 | Milvus Lite | 本地文件，无需独立部署 |
| 关系数据库 | MySQL 8.x | Docker 容器 |
| Embedding | SiliconFlow API (bge-large-zh-v1.5) | 1024 维 |
| Reranker | SiliconFlow API (bge-reranker-v2-m3) | 多 key 负载均衡 |
| LLM | DeepSeek API | 规整/分类/HyDE |
| Agent | LangGraph | 状态图编排 |
| BM25 | jieba + rank_bm25 | 关键词召回 |
| ASR | 阿里云NLS API | 实时语音识别 |
| 追踪 | LangSmith | 全链路追踪 |

## 环境要求

- Python 3.10+
- Docker Desktop（用于启动 MySQL）
- DeepSeek API Key（去 https://platform.deepseek.com 注册获取）
- SiliconFlow API Keys（去 https://siliconflow.cn 注册获取，支持多 key 负载均衡）

## 快速开始

### 方式一：一键搭建（推荐）

Windows:
```bash
setup.bat
```

Linux/Mac:
```bash
chmod +x setup.sh
./setup.sh
```

脚本会自动完成：安装依赖 -> 启动MySQL -> 初始化数据库

### 方式二：手动搭建

1. 安装依赖
```bash
pip install -r requirements.txt
```

2. 配置环境变量
```bash
cp .env.template .env
# 编辑 .env，填入 DeepSeek API Key 和 SiliconFlow API Keys
```

3. 配置阿里云NLS API Key（.env中ALICLOUD_ASR_APP_KEY/ACCESS_KEY_ID/ACCESS_KEY_SECRET/HOTWORDS_ID，无需下载本地模型）

4. 启动 MySQL + 初始化数据库
```bash
docker compose -f docker-compose.dev.yml up -d mysql
python scripts/data/init_db.py dev
```

5. 启动服务
```bash
python main.py
```

访问 API 文档: http://localhost:8000/docs

## Docker 启动

```bash
# 开发环境（热更新）
docker compose -f docker-compose.dev.yml up -d

# 生产环境
docker compose up -d
```

## 测试

```bash
# 单元测试（1240 passed）
python -m pytest tests/ -q --ignore=tests/integration

# 集成测试
python -m pytest tests/integration/ -m integration -v

# 基准测试
python -m pytest tests/benchmark/ -q
```

测试文件 59 个，测试用例 1240 个，集成测试 13 个文件，基准测试 5 个。

## 环境说明

通过环境变量 ETC_QA_ENV 切换：

| 环境 | 用途 | MySQL 库 | 启动方式 |
|------|------|----------|---------|
| dev | 日常开发 | etc_qa | python main.py |
| test | 测试 | etc_qa_test | ETC_QA_ENV=test python main.py |
| prod | 生产 | etc_qa | docker compose up -d |

## 项目结构

```
etc_qa/
├── agent/           # LangGraph Agent（问题规整/分类/HyDE/入库改写）
├── api/             # FastAPI 路由
├── asr/             # 语音识别
├── config/          # 配置文件（YAML + Pydantic校验）
├── db/              # MySQL + Milvus 客户端
├── models/                # 模型文件（ASR已改用API，无需本地模型）
├── rag/             # 召回 + Reranker + 阈值判定 + SiliconFlow API客户端
├── prompt/          # 提示词模板管理
├── scheduler/       # 定时任务调度
├── alert/           # 异常告警 + 通知
├── scripts/         # 数据初始化/评估/维护脚本
├── tests/           # 单元测试 + 集成测试 + 基准测试
├── docs/            # 文档
├── docker-compose.dev.yml  # 开发环境
├── docker-compose.yml      # 生产环境
├── setup.bat / setup.sh    # 一键搭建脚本
└── .env.template           # 环境变量模板
```

## 文档

| 文档 | 说明 |
|------|------|
| [开发环境搭建.md](../docs/guides/开发环境搭建.md) | 队友上手指南 |
| [Git使用教程.md](../docs/tutorials/Git使用教程.md) | Git 图形界面 + 命令行 |
| [Docker使用教程.md](../docs/tutorials/Docker使用教程.md) | Docker 使用指南 |
| [后端架构图.md](../docs/architecture/后端架构图.md) | 系统架构、核心链路 |
| [后端目录结构.md](../docs/architecture/后端目录结构.md) | 目录结构 + 代码调用关系 |
| [API接口文档.md](../docs/api/API接口文档.md) | REST API 说明 |
| [数据库设计文档.md](../docs/database/数据库设计文档.md) | 表结构 + 字段说明 |
| [开发规范.md](../docs/standards/开发规范.md) | 代码规范、提交规范 |
| [交接清单.md](../docs/guides/交接清单.md) | 已完成/待开发/注意事项 |
| [开发规范.md](../docs/开发规范.md) | 代码规范、提交规范 |
| [交接清单.md](../docs/交接清单.md) | 已完成/待开发/注意事项 |
