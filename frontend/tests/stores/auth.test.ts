import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../../src/stores/auth'

describe('useAuthStore', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  describe('initial state', () => {
    it('starts empty with no sessionStorage', () => {
      const store = useAuthStore()
      expect(store.token).toBe('')
      expect(store.role).toBe('')
      expect(store.username).toBe('')
      expect(store.dept).toBe('')
      expect(store.impersonatorToken).toBe('')
      expect(store.permissions).toEqual([])
    })

    it('reads from sessionStorage on init', () => {
      sessionStorage.setItem('token', 'tok123')
      sessionStorage.setItem('userRole', 'admin')
      sessionStorage.setItem('userName', 'alice')
      sessionStorage.setItem('userDept', 'aftersale')
      const store = useAuthStore()
      expect(store.token).toBe('tok123')
      expect(store.role).toBe('admin')
      expect(store.username).toBe('alice')
      expect(store.dept).toBe('aftersale')
    })
  })

  describe('roleText', () => {
    it.each([
      ['admin', '业务管理员'],
      ['superadmin', '超级管理员'],
      ['ops', '运维工程师'],
      ['service', '客服'],
      ['dept', '部门处理员'],
    ])('maps %s to %s', (role, expected) => {
      const store = useAuthStore()
      store.setAuth('t', role, '')
      expect(store.roleText).toBe(expected)
    })

    it('returns unknown for unrecognized role', () => {
      const store = useAuthStore()
      store.setAuth('t', 'god', '')
      expect(store.roleText).toBe('god')
    })

    it('returns 未知账号 for empty role', () => {
      const store = useAuthStore()
      expect(store.roleText).toBe('未知账号')
    })
  })

  describe('setAuth', () => {
    it('sets token/role/dept and writes to sessionStorage', () => {
      const store = useAuthStore()
      store.setAuth('tok', 'admin', 'dept_x')
      expect(store.token).toBe('tok')
      expect(store.role).toBe('admin')
      expect(store.dept).toBe('dept_x')
      expect(sessionStorage.getItem('token')).toBe('tok')
      expect(sessionStorage.getItem('userRole')).toBe('admin')
      expect(sessionStorage.getItem('userDept')).toBe('dept_x')
    })

    it('sets username when provided', () => {
      const store = useAuthStore()
      store.setAuth('tok', 'admin', '', 'bob')
      expect(store.username).toBe('bob')
      expect(sessionStorage.getItem('userName')).toBe('bob')
    })

    it('does not overwrite username when not provided', () => {
      const store = useAuthStore()
      store.setAuth('tok', 'admin', '', 'bob')
      store.setAuth('tok2', 'service', '')
      expect(store.username).toBe('bob')
    })
  })

  describe('setPermissions', () => {
    it('sets permissions and writes to sessionStorage', () => {
      const store = useAuthStore()
      store.setPermissions(['read', 'write'])
      expect(store.permissions).toEqual(['read', 'write'])
      expect(sessionStorage.getItem('permissions')).toBe(JSON.stringify(['read', 'write']))
    })
  })

  describe('impersonation', () => {
    it('isImpersonating is false by default', () => {
      const store = useAuthStore()
      expect(store.isImpersonating).toBe(false)
    })

    it('startImpersonation saves original token and switches', () => {
      const store = useAuthStore()
      store.setAuth('orig_tok', 'superadmin', '', 'super')
      store.startImpersonation('imp_tok', 'service', '', 'service_user')
      expect(store.token).toBe('imp_tok')
      expect(store.role).toBe('service')
      expect(store.impersonatorToken).toBe('orig_tok')
      expect(store.isImpersonating).toBe(true)
      expect(sessionStorage.getItem('impersonator_token')).toBe('orig_tok')
      expect(sessionStorage.getItem('impersonator_role')).toBe('superadmin')
    })

    it('exitImpersonation restores original token and role', () => {
      const store = useAuthStore()
      store.setAuth('orig_tok', 'superadmin', '', 'super')
      store.startImpersonation('imp_tok', 'service', '', 'service_user')
      store.exitImpersonation()
      expect(store.token).toBe('orig_tok')
      expect(store.role).toBe('superadmin')
      expect(store.impersonatorToken).toBe('')
      expect(store.isImpersonating).toBe(false)
    })

    it('exitImpersonation does nothing without impersonatorToken', () => {
      const store = useAuthStore()
      store.setAuth('tok', 'admin', '')
      store.exitImpersonation()
      expect(store.token).toBe('tok')
      expect(store.role).toBe('admin')
    })
  })

  describe('clearAuth', () => {
    it('clears all state and sessionStorage', () => {
      const store = useAuthStore()
      store.setAuth('tok', 'admin', 'dept_x', 'alice')
      store.setPermissions(['read'])
      store.startImpersonation('imp_tok', 'service', '', 'svc')
      store.clearAuth()
      expect(store.token).toBe('')
      expect(store.role).toBe('')
      expect(store.username).toBe('')
      expect(store.dept).toBe('')
      expect(store.impersonatorToken).toBe('')
      expect(store.permissions).toEqual([])
      expect(sessionStorage.getItem('token')).toBeNull()
      expect(sessionStorage.getItem('userRole')).toBeNull()
      expect(sessionStorage.getItem('permissions')).toBeNull()
    })
  })
})
