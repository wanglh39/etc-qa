# 贡献指南

感谢参与本项目！请阅读以下指南。

---

## 开发环境

详见 [docs/guides/开发环境搭建.md](docs/guides/开发环境搭建.md)。

### 前置条件

| 工具 | 版本 |
|------|------|
| Python | 3.10+ |
| Node.js | 18+ |
| MySQL | 8.x |
| Git | 最新版 |

### 快速启动

```bash
# 后端
cd backend
conda create -n etc_qa python=3.10 -y && conda activate etc_qa
pip install -r requirements.txt
cp .env.example .env  # 填入 DEEPSEEK_API_KEY
python scripts/data/init_db.py test
python main.py

# 前端
cd frontend
npm install
npm run dev
```

---

## 开发流程

### 1. 分支策略

```
main          ← 生产分支（保护）
  └── dev     ← 开发分支
      ├── feat/xxx   ← 功能分支
      ├── fix/xxx    ← 修复分支
      └── refactor/xxx
```

### 2. 提交规范

格式：`<type>(<scope>): <subject>`

| type | 说明 |
|------|------|
| feat | 新功能 |
| fix | 修复 bug |
| refactor | 重构 |
| docs | 文档 |
| test | 测试 |
| chore | 构建/配置 |

示例：`feat(agent): 合并 structure_ingest 和 classify 为一步 LLM 调用`

### 3. 提交前检查

**后端**：
```bash
cd backend
python -m pytest tests/ -x -q -o addopts="" --ignore=tests/integration  # 单元测试
ruff check .  # lint
```

**前端**：
```bash
cd frontend
npm run test  # 单元测试 + 覆盖率
npx vue-tsc --noEmit  # 类型检查
npm run lint  # lint
```

Husky pre-commit 钩子会自动执行 lint-staged（ESLint + Prettier）。

### 4. PR 流程

1. 从 `dev` 创建功能分支
2. 开发 + 写测试 + 更新文档
3. 本地通过所有检查
4. 提交 PR 到 `dev`，描述改动内容
5. CI 通过后 review 合并

---

## 代码规范

详见 [docs/standards/开发规范.md](docs/standards/开发规范.md)。

### 后端（Python）
- 遵循 PEP 8
- 类型注解必加
- 单文件不超过 300 行
- 不写废话注释，关键逻辑写"为什么"
- 禁止硬编码业务数据，用 config_center 或 config.yaml

### 前端（TypeScript/Vue）
- `<script setup>` Composition API
- 全量 TypeScript，vue-tsc 类型检查必须通过
- 不加注释（除非用户明确要求）
- ESLint + Prettier 格式化

---

## 测试要求

| 类型 | 覆盖范围 | 命令 |
|------|---------|------|
| 后端单元 | 每个源文件有对应测试 | `pytest tests/ -q` |
| 后端集成 | 模块间交互 | `pytest tests/integration/ -v` |
| 后端基准 | 性能基准 | `pytest tests/benchmark/ -q` |
| 前端单元 | 组件/工具/Store | `npm run test` |
| 前端 E2E | 关键用户流程 | `npx playwright test` |
| 契约测试 | 前后端 API 一致性 | 包含在前端测试中 |

覆盖率门槛：语句/分支/函数/行 ≥ 80%

---

## 文档同步

改代码后同步更新对应文档：

| 改动类型 | 需更新的文档 |
|---------|------------|
| 后端结构 | docs/architecture/后端目录结构.md + 后端技术设计.md |
| 前端结构 | docs/architecture/前端目录结构.md + 前端技术设计.md |
| API 接口 | docs/api/API接口文档.md |
| 数据库 | docs/database/数据库设计文档.md |
| 权限/角色 | docs/security/安全设计文档.md |
| 部署/运维 | docs/ops/运维手册.md |

---

## 角色账号（开发环境）

| 账号 | 密码 | 角色 | 默认页面 |
|------|------|------|---------|
| superadmin | 123456 | 超级管理员 | /workbench/admin/account |
| admin | 123456 | 业务管理员 | /workbench/admin/dashboard |
| ops | 123456 | 运维工程师 | /workbench/admin/status |
| service | 123456 | 客服 | /service |
| dept | 123456 | 部门处理员 | /dept/handle/{dept} |