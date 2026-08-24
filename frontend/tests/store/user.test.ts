import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUserStore } from '../../src/store/user'

describe('useUserStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts with admin role and full permissions', () => {
    const store = useUserStore()
    expect(store.role).toBe('admin')
    expect(store.permission).toEqual(['workbench', 'knowledge', 'audit', 'dashboard', 'system'])
  })

  describe('hasPerm', () => {
    it('returns true for existing permission', () => {
      const store = useUserStore()
      expect(store.hasPerm('workbench')).toBe(true)
      expect(store.hasPerm('system')).toBe(true)
    })

    it('returns false for missing permission', () => {
      const store = useUserStore()
      expect(store.hasPerm('super_secret')).toBe(false)
    })
  })

  describe('switchRole', () => {
    it('switches to operator and removes system permission', () => {
      const store = useUserStore()
      store.switchRole('operator')
      expect(store.role).toBe('operator')
      expect(store.permission).toEqual(['workbench', 'knowledge', 'audit', 'dashboard'])
      expect(store.hasPerm('system')).toBe(false)
    })

    it('switches to admin and restores system permission', () => {
      const store = useUserStore()
      store.switchRole('operator')
      store.switchRole('admin')
      expect(store.role).toBe('admin')
      expect(store.permission).toEqual(['workbench', 'knowledge', 'audit', 'dashboard', 'system'])
      expect(store.hasPerm('system')).toBe(true)
    })

    it('switches to unknown role and keeps full permissions', () => {
      const store = useUserStore()
      store.switchRole('unknown')
      expect(store.role).toBe('unknown')
      expect(store.hasPerm('system')).toBe(true)
    })
  })
})
