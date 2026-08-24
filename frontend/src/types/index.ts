// src/types/index.ts

// ================= 原有代码 =================

// 工作台用户类型
export interface WorkUser {
  userId: string
}

// 待审核工单
export interface PendingAuditItem {
  orderId: string
  question: string
  confidence: number
  submitTime: string
}

// 待流转工单
export interface TransferTicketItem {
  ticketId: string
  userDesc: string
  currentDept: string
  deadline: string
}

// 知识库分类
export interface CategoryItem {
  id: string
  label: string
  parentId: string | null
  children?: CategoryItem[]
}

// 知识库条目
export interface KnowledgeItem {
  ID: string
  questionTitle: string
  belongClass: string
  status: '已上架' | '已下架'
}

// 分页通用事件参数
export type PageSizeChange = (val: number) => void
export type PageCurrentChange = (page: number) => void

// ================= ✅ 新增修复代码 =================

/**
 * 普通用户信息类型
 * 用于 service/index.vue 中的 userList
 */
export interface UserInfo {
  userId: string
  userName?: string
  avatar?: string
  [key: string]: any // 允许任意字段，避免 TS 报错
}

/**
 * 工单/任务通用类型
 * 用于 workbench/index.vue 中的 doneUserList, pendingUserList 等
 */
export interface TicketItem {
  id: string
  title?: string
  status?: string
  createTime?: string
  assignee?: string
  [key: string]: any // 允许任意字段
}
