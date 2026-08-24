import { describe, it, expect, vi, beforeEach } from 'vitest'
import request from '@/utils/request'
import { getStats, getStatsTrend } from '@/api/dashboard'

vi.mock('@/utils/request')

const mockedRequest = vi.mocked(request, true)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('api/dashboard', () => {
  describe('getStats', () => {
    it('GETs /stats and returns res.data', async () => {
      const fakeData = {
        qa_total: 100,
        qa_active: 80,
        qa_deprecated: 10,
        qa_archived: 10,
        work_order_total: 50,
        work_order_submitted: 20,
        work_order_processed: 30,
        category_stats: { 退费: 30, 咨询: 20 },
      }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })

      const result = await getStats()

      expect(mockedRequest.get).toHaveBeenCalledWith('/stats')
      expect(result).toEqual(fakeData)
    })
  })

  describe('getStatsTrend', () => {
    it('GETs /stats/trend with days param when provided', async () => {
      const fakeData = { dates: ['2024-01-01'], work_order_counts: [5], qa_new_counts: [3] }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })

      const result = await getStatsTrend(7)

      expect(mockedRequest.get).toHaveBeenCalledWith('/stats/trend', { params: { days: 7 } })
      expect(result).toEqual(fakeData)
    })

    it('GETs /stats/trend with undefined days when not provided', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: {} })
      await getStatsTrend()
      expect(mockedRequest.get).toHaveBeenCalledWith('/stats/trend', {
        params: { days: undefined },
      })
    })
  })
})
