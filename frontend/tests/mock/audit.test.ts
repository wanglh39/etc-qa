import { describe, it, expect } from 'vitest'
import { waitAuditList, auditRecordList } from '@/mock/audit'

describe('mock/audit', () => {
  it('waitAuditList has 2 pending items', () => {
    expect(waitAuditList).toHaveLength(2)
    waitAuditList.forEach((a) => {
      expect(a).toHaveProperty('id')
      expect(a).toHaveProperty('question')
      expect(a).toHaveProperty('draftAnswer')
      expect(a).toHaveProperty('categoryName')
      expect(a).toHaveProperty('confidence')
      expect(a).toHaveProperty('createTime')
    })
  })

  it('confidence values are between 0 and 100', () => {
    waitAuditList.forEach((a) => {
      expect(a.confidence).toBeGreaterThanOrEqual(0)
      expect(a.confidence).toBeLessThanOrEqual(100)
    })
  })

  it('auditRecordList has 2 records', () => {
    expect(auditRecordList).toHaveLength(2)
    auditRecordList.forEach((r) => {
      expect(r).toHaveProperty('id')
      expect(r).toHaveProperty('question')
      expect(r).toHaveProperty('result')
      expect(r).toHaveProperty('auditTime')
      expect(r).toHaveProperty('auditor')
    })
  })

  it('audit results are pass or reject', () => {
    auditRecordList.forEach((r) => {
      expect(['pass', 'reject']).toContain(r.result)
    })
  })
})
