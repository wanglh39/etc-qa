# ADR-002: 5 角色 RBAC 而非 3 角色

**状态**：已接受  
**日期**：2026-08-15

## 背景

系统需要角色权限控制。初始设计为 3 角色（admin/service/dept），后扩展为 5 角色。

## 决策

采用 **5 角色 RBAC**：superadmin / admin / ops / service / dept

## 理由

1. **超管分离**：superadmin 管账号/角色/日志，admin 管业务/内容。避免管理员既管系统又管业务，符合企业级权限分离原则
2. **运维独立**：ops 角色管监控/调度/告警，与业务管理员(admin)职责不交叉。企业级标准要求开发/运维分离
3. **模拟登录**：superadmin 可模拟其他角色身份排查问题，需要独立角色
4. **前后端一致**：后端 require_role + 前端 roleAuth 双重校验，5 角色各有明确权限边界

## 代价

- 角色多，权限配置复杂度增加（但通过 roles 表 permissions JSON 字段管理，可动态配置）
- 前端菜单需按角色硬编码（已通过 buildMenu(permissions) 动态生成解决）

## 参考

- [RBAC 标准](https://en.wikipedia.org/wiki/Role-based_access_control)
- docs/security/安全设计文档.md