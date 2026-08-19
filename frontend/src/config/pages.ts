import type { Component } from 'vue'
import {
  DataLine, Document, Setting, UserFilled, Monitor, Bell,
  Service, Ticket, Money
} from '@element-plus/icons-vue'

export interface PageConfig {
  path: string
  label: string
  icon: Component
  group: string
}

export const ALL_PAGES: PageConfig[] = [
  { path: '/workbench/admin/dashboard', label: '数据看板', icon: DataLine, group: '' },
  { path: '/workbench/admin/auditList', label: '待审核列表', icon: Document, group: '业务管理' },
  { path: '/workbench/admin/auditHistory', label: '审核历史', icon: Document, group: '业务管理' },
  { path: '/workbench/admin/knowledge', label: '知识库管理', icon: Document, group: '内容管理' },
  { path: '/workbench/admin/category', label: '分类管理', icon: Setting, group: '内容管理' },
  { path: '/workbench/admin/config', label: '配置管理', icon: Setting, group: '内容管理' },
  { path: '/workbench/admin/account', label: '账号管理', icon: UserFilled, group: '系统管理' },
  { path: '/workbench/admin/role', label: '角色管理', icon: UserFilled, group: '系统管理' },
  { path: '/workbench/admin/operationLog', label: '操作日志', icon: Document, group: '系统管理' },
  { path: '/workbench/admin/impersonate', label: '模拟登录', icon: UserFilled, group: '系统管理' },
  { path: '/workbench/admin/status', label: '系统状态总览', icon: Monitor, group: '运维管理' },
  { path: '/workbench/admin/monitor', label: '性能监控看板', icon: Monitor, group: '运维管理' },
  { path: '/workbench/admin/scheduler', label: '定时任务调度', icon: Setting, group: '运维管理' },
  { path: '/workbench/admin/alert', label: '异常告警', icon: Bell, group: '运维管理' },
  { path: '/service', label: '客服工作台', icon: Service, group: '' },
  { path: '/dept/handle/aftersale', label: '售后工单处理', icon: Ticket, group: '' },
  { path: '/dept/handle/ops', label: '技术运维工单处理', icon: Monitor, group: '' },
  { path: '/dept/handle/finance', label: '财务工单处理', icon: Money, group: '' },
]

export function getPageLabel(path: string): string {
  return ALL_PAGES.find(p => p.path === path)?.label || path
}

export interface MenuGroup {
  label: string
  icon: Component
  items: PageConfig[]
}

export function buildMenu(permissions: string[]): MenuGroup[] {
  const allowed = ALL_PAGES.filter(p => permissions.includes(p.path))
  const groups: MenuGroup[] = []
  const groupMap = new Map<string, PageConfig[]>()

  for (const page of allowed) {
    if (!groupMap.has(page.group)) groupMap.set(page.group, [])
    groupMap.get(page.group)!.push(page)
  }

  for (const [groupLabel, items] of groupMap) {
    if (groupLabel === '') {
      for (const item of items) {
        groups.push({ label: '', icon: item.icon, items: [item] })
      }
    } else {
      groups.push({ label: groupLabel, icon: items[0].icon, items })
    }
  }

  return groups
}