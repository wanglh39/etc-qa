import { describe, it, expect, vi } from 'vitest'

vi.mock('@element-plus/icons-vue', () => ({
  DataLine: { name: 'DataLine' },
  Document: { name: 'Document' },
  Setting: { name: 'Setting' },
  UserFilled: { name: 'UserFilled' },
  Monitor: { name: 'Monitor' },
  Bell: { name: 'Bell' },
  Service: { name: 'Service' },
  Ticket: { name: 'Ticket' },
  Money: { name: 'Money' },
}))

import { ALL_PAGES, getPageLabel, buildMenu } from '@/config/pages'

describe('config/pages', () => {
  describe('ALL_PAGES', () => {
    it('has 18 page configs', () => {
      expect(ALL_PAGES).toHaveLength(18)
    })

    it('each page has required fields', () => {
      ALL_PAGES.forEach((p) => {
        expect(p).toHaveProperty('path')
        expect(p).toHaveProperty('label')
        expect(p).toHaveProperty('icon')
        expect(p).toHaveProperty('group')
      })
    })

    it('paths are unique', () => {
      const paths = ALL_PAGES.map((p) => p.path)
      expect(new Set(paths).size).toBe(paths.length)
    })
  })

  describe('getPageLabel', () => {
    it('returns label for known path', () => {
      expect(getPageLabel('/service')).toBe('客服工作台')
      expect(getPageLabel('/workbench/admin/dashboard')).toBe('数据看板')
    })

    it('returns path for unknown path', () => {
      expect(getPageLabel('/unknown')).toBe('/unknown')
    })

    it('returns path for empty string', () => {
      expect(getPageLabel('')).toBe('')
    })
  })

  describe('buildMenu', () => {
    it('returns empty array for no permissions', () => {
      expect(buildMenu([])).toEqual([])
    })

    it('returns all pages when all permissions granted', () => {
      const allPaths = ALL_PAGES.map((p) => p.path)
      const menu = buildMenu(allPaths)
      expect(menu.length).toBeGreaterThan(0)
    })

    it('groups pages by group label', () => {
      const menu = buildMenu(['/workbench/admin/auditList', '/workbench/admin/auditHistory'])
      expect(menu).toHaveLength(1)
      expect(menu[0].label).toBe('业务管理')
      expect(menu[0].items).toHaveLength(2)
    })

    it('ungrouped pages become individual groups', () => {
      const menu = buildMenu(['/service'])
      expect(menu).toHaveLength(1)
      expect(menu[0].label).toBe('')
      expect(menu[0].items).toHaveLength(1)
    })

    it('mixed grouped and ungrouped pages', () => {
      const menu = buildMenu([
        '/workbench/admin/dashboard',
        '/workbench/admin/auditList',
        '/workbench/admin/auditHistory',
      ])
      const ungrouped = menu.filter((g) => g.label === '')
      const grouped = menu.filter((g) => g.label !== '')
      expect(ungrouped).toHaveLength(1)
      expect(grouped).toHaveLength(1)
      expect(grouped[0].items).toHaveLength(2)
    })

    it('filters out pages not in permissions', () => {
      const menu = buildMenu(['/service'])
      expect(menu).toHaveLength(1)
      expect(menu[0].items[0].path).toBe('/service')
    })
  })
})
