import { describe, it, expect } from 'vitest'
import { dashboardMock } from '@/mock/dashboard'

describe('mock/dashboard', () => {
  it('has all required numeric fields', () => {
    expect(typeof dashboardMock.todayCount).toBe('number')
    expect(typeof dashboardMock.finishCount).toBe('number')
    expect(typeof dashboardMock.auditCount).toBe('number')
    expect(typeof dashboardMock.ticketCount).toBe('number')
  })

  it('lineX and lineY have same length', () => {
    expect(dashboardMock.lineX).toHaveLength(dashboardMock.lineY.length)
  })

  it('pieData has 4 categories', () => {
    expect(dashboardMock.pieData).toHaveLength(4)
    dashboardMock.pieData.forEach((p) => {
      expect(p).toHaveProperty('name')
      expect(p).toHaveProperty('value')
      expect(typeof p.value).toBe('number')
    })
  })
})
