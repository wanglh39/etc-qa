import { describe, it, expect } from 'vitest'
import { sessionList, newMockSession } from '@/mock/workbench'

describe('mock/workbench', () => {
  it('sessionList has 2 sessions', () => {
    expect(sessionList).toHaveLength(2)
  })

  it('each session has required fields', () => {
    sessionList.forEach((s) => {
      expect(s).toHaveProperty('userId')
      expect(s).toHaveProperty('problemAbstract')
      expect(s).toHaveProperty('accessTime')
      expect(s).toHaveProperty('audioSrc')
      expect(s).toHaveProperty('voiceText')
      expect(s).toHaveProperty('ragReply')
      expect(s).toHaveProperty('status')
    })
  })

  it('sessions have correct userIds', () => {
    expect(sessionList[0].userId).toBe('U0001')
    expect(sessionList[1].userId).toBe('U0002')
  })

  it('newMockSession has userId U0003', () => {
    expect(newMockSession.userId).toBe('U0003')
    expect(newMockSession.status).toBe('normal')
  })
})
