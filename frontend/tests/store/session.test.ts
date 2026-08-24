import { describe, it, expect, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useSessionStore } from '../../src/store/session'

describe('useSessionStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('starts with pendingTicketNum=1 and empty noticeList', () => {
    const store = useSessionStore()
    expect(store.pendingTicketNum).toBe(1)
    expect(store.noticeList).toEqual([])
  })

  describe('updateNotice', () => {
    it('adds message to noticeList', () => {
      const store = useSessionStore()
      store.updateNotice('ticket A')
      expect(store.noticeList).toEqual(['ticket A'])
    })

    it('updates pendingTicketNum to match noticeList length', () => {
      const store = useSessionStore()
      store.updateNotice('msg1')
      expect(store.pendingTicketNum).toBe(1)
      store.updateNotice('msg2')
      expect(store.pendingTicketNum).toBe(2)
      store.updateNotice('msg3')
      expect(store.pendingTicketNum).toBe(3)
    })

    it('handles multiple messages', () => {
      const store = useSessionStore()
      for (let i = 0; i < 5; i++) {
        store.updateNotice(`msg${i}`)
      }
      expect(store.noticeList).toHaveLength(5)
      expect(store.pendingTicketNum).toBe(5)
    })
  })
})
