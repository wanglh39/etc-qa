# ETC客服QA智能检索系统 — 前端

## 技术栈

| 技术 | 版本 | 用途 |
|------|------|------|
| Vue 3 | 3.5 | 前端框架 |
| TypeScript | 6.0 | 类型安全 |
| Vite | 8.1 | 构建工具 |
| Element Plus | 2.14 | UI 组件库 |
| ECharts | 6.1 | 数据可视化 |
| Pinia | 3.0 | 状态管理 |
| Vue Router | 4.6 | 路由 + 权限守卫 |
| Axios | 1.18 | HTTP 请求 |
| WangEditor | 5.1 | 富文本编辑器 |

## 角色体系 (5角色 RBAC)

| 角色 | 定位 | 默认首页 |
|------|------|---------|
| superadmin | 超级管理员 | /workbench/admin/account |
| ops | 运维工程师 | /workbench/admin/status |
| admin | 业务管理员 | /workbench/admin/dashboard |
| service | 客服 | /service |
| dept | 部门处理员 | /dept/handle/{dept} |

## 开发

```bash
npm install        # 安装依赖
npm run dev        # 启动开发服务器 (localhost:5173)
npm run build      # 类型检查 + 构建
```

## 测试

```bash
npm run test:run       # 单元测试 (678用例)
npm run test:coverage  # 覆盖率报告 (门槛80%)
npm run e2e            # E2E测试 (Playwright)
npm run lint           # ESLint检查
npm run format:check   # Prettier格式检查
```

## 目录结构

```
frontend/
├── src/
│   ├── api/           # API 请求层 (8个模块)
│   ├── components/    # 公共组件 (6个 + layout/3个)
│   ├── composables/   # 组合式函数 (useStreamingASR)
│   ├── config/        # 页面配置
│   ├── mock/          # 静态 mock 数据
│   ├── pages/         # 页面 (20个)
│   ├── router/        # 路由 + 权限守卫
│   ├── stores/        # Pinia 状态管理
│   ├── utils/         # 工具函数
│   └── types/         # TypeScript 类型定义
├── tests/             # 单元测试 (58文件, 681用例)
│   ├── contract/      # 前后端契约测试
│   └── helpers/       # 共享测试工具
├── e2e/               # E2E 测试 (Playwright)
├── vitest.config.ts   # 测试配置 (覆盖率门槛80%)
├── playwright.config.ts # E2E配置
└── eslint.config.js   # ESLint配置
```

## 认证流程

1. 登录 → POST /api/auth/login → 获取 JWT token
2. token 存入 sessionStorage（关浏览器自动清除）
3. 路由守卫 beforeEach → 校验 token + 角色权限
4. Axios 拦截器自动添加 Bearer token
5. 401 → 清除认证 → 跳转登录页
