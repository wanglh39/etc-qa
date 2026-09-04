import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  createRouter: vi.fn(() => ({
    beforeEach: vi.fn(),
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    options: { routes: [] },
  })),
  createWebHistory: vi.fn(),
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
}))

import { useAuthStore } from '@/stores/auth'
import router, { getDefaultPath } from '@/router'

describe('router/index', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  describe('getDefaultPath', () => {
    it('returns /workbench/admin/account for superadmin', () => {
      const authStore = useAuthStore()
      authStore.setAuth('tok', 'superadmin', '')
      authStore.setPermissions(['/workbench/admin/account', '/workbench/admin/role'])
      expect(getDefaultPath('superadmin')).toBe('/workbench/admin/account')
    })

    it('returns /workbench/admin/status for ops', () => {
      const authStore = useAuthStore()
      authStore.setAuth('tok', 'ops', '')
      authStore.setPermissions(['/workbench/admin/status', '/workbench/admin/monitor'])
      expect(getDefaultPath('ops')).toBe('/workbench/admin/status')
    })

    it('returns /workbench/admin/dashboard for admin', () => {
      const authStore = useAuthStore()
      authStore.setAuth('tok', 'admin', '')
      authStore.setPermissions(['/workbench/admin/dashboard', '/workbench/admin/knowledge'])
      expect(getDefaultPath('admin')).toBe('/workbench/admin/dashboard')
    })

    it('returns /service for service', () => {
      const authStore = useAuthStore()
      authStore.setAuth('tok', 'service', '')
      authStore.setPermissions(['/service'])
      expect(getDefaultPath('service')).toBe('/service')
    })

    it('returns /dept/handle/aftersale for dept with aftersale dept', () => {
      const authStore = useAuthStore()
      authStore.setAuth('tok', 'dept', 'aftersale')
      authStore.setPermissions(['/dept/handle/aftersale'])
      expect(getDefaultPath('dept')).toBe('/dept/handle/aftersale')
    })

    it('returns /dept/handle/finance for dept with finance dept', () => {
      const authStore = useAuthStore()
      authStore.setAuth('tok', 'dept', 'finance')
      authStore.setPermissions(['/dept/handle/finance'])
      expect(getDefaultPath('dept')).toBe('/dept/handle/finance')
    })

    it('returns /dept/handle/aftersale for dept with empty dept', () => {
      const authStore = useAuthStore()
      authStore.setAuth('tok', 'dept', '')
      expect(getDefaultPath('dept')).toBe('/dept/handle/aftersale')
    })

    it('returns first matching page for unknown role with permissions', () => {
      const authStore = useAuthStore()
      authStore.setAuth('tok', 'unknown', '')
      authStore.setPermissions(['/workbench/admin/dashboard', '/custom/path'])
      expect(getDefaultPath('unknown')).toBe('/workbench/admin/dashboard')
    })

    it('returns default admin path for unknown role without permissions', () => {
      const authStore = useAuthStore()
      authStore.setAuth('tok', 'unknown', '')
      expect(getDefaultPath('unknown')).toBe('/workbench/admin/dashboard')
    })
  })

  describe('router instance', () => {
    it('exports a router object', () => {
      expect(router).toBeDefined()
      expect(router.beforeEach).toBeDefined()
    })
  })
})
