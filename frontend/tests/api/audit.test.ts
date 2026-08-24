import { describe, it, expect, vi, beforeEach } from 'vitest'
import request from '@/utils/request'
import { getWorkOrders, getWorkOrderStats, processAgent, getAuditHistory } from '@/api/audit'

vi.mock('@/utils/request')

const mockedRequest = vi.mocked(request, true)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('api/audit', () => {
  describe('getWorkOrders', () => {
    it('GETs /work_orders with all params', async () => {
      const fakeData = { items: [], total: 0, page: 1, page_size: 20 }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })

      const result = await getWorkOrders({
        page: 1,
        page_size: 20,
        status: 'submitted',
        dept: 'aftersale',
      })

      expect(mockedRequest.get).toHaveBeenCalledWith('/work_orders', {
        params: { page: 1, page_size: 20, status: 'submitted', dept: 'aftersale' },
      })
      expect(result).toEqual(fakeData)
    })

    it('GETs /work_orders with partial params', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: {} })
      await getWorkOrders({ page: 2 })
      expect(mockedRequest.get).toHaveBeenCalledWith('/work_orders', { params: { page: 2 } })
    })

    it('GETs /work_orders with empty params', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: {} })
      await getWorkOrders({})
      expect(mockedRequest.get).toHaveBeenCalledWith('/work_orders', { params: {} })
    })
  })

  describe('getWorkOrderStats', () => {
    it('GETs /work_orders/stats', async () => {
      const fakeData = { total: 100, submitted: 30, answered: 20, processed: 50, today: 5 }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })

      const result = await getWorkOrderStats()

      expect(mockedRequest.get).toHaveBeenCalledWith('/work_orders/stats')
      expect(result).toEqual(fakeData)
    })
  })

  describe('processAgent', () => {
    it('POSTs to /agent/process with question and optional fields', async () => {
      const fakeData = {
        question: '怎么退费',
        answer: '联系客服',
        internal_process: '转接',
        feedback_dept: 'aftersale',
        is_duplicate: false,
        similarity_score: 0.9,
        category_l1: '售后',
        category_l2: '退费',
        category_confidence: 0.95,
        needs_review: false,
        review_highlights: [],
        current_step: 'done',
      }
      mockedRequest.post.mockResolvedValueOnce({ data: fakeData })

      const result = await processAgent({ question: '怎么退费', answer: '联系客服' })

      expect(mockedRequest.post).toHaveBeenCalledWith('/agent/process', {
        question: '怎么退费',
        answer: '联系客服',
      })
      expect(result).toEqual(fakeData)
    })

    it('POSTs with minimal payload', async () => {
      mockedRequest.post.mockResolvedValueOnce({ data: {} })
      await processAgent({ question: 'test' })
      expect(mockedRequest.post).toHaveBeenCalledWith('/agent/process', { question: 'test' })
    })
  })

  describe('getAuditHistory', () => {
    it('GETs /audit/history with pagination params', async () => {
      const fakeData = { items: [], total: 0, page: 1, page_size: 20 }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })

      const result = await getAuditHistory({ page: 1, page_size: 20 })

      expect(mockedRequest.get).toHaveBeenCalledWith('/audit/history', {
        params: { page: 1, page_size: 20 },
      })
      expect(result).toEqual(fakeData)
    })

    it('GETs /audit/history with empty params', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: {} })
      await getAuditHistory({})
      expect(mockedRequest.get).toHaveBeenCalledWith('/audit/history', { params: {} })
    })
  })
})
