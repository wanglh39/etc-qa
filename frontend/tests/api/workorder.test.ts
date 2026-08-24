import { describe, it, expect, vi, beforeEach } from 'vitest'
import request from '@/utils/request'
import { createWorkOrder, getWorkOrderDetail, replyWorkOrder } from '@/api/workorder'

vi.mock('@/utils/request')

const mockedRequest = vi.mocked(request, true)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('api/workorder', () => {
  const createParams = {
    service_id: 's1',
    customer_name: '张三',
    phone: '13800000000',
    problem_type: '退费',
    next_dept: 'aftersale',
    priority: 'high',
    detail_desc: '描述',
  }

  describe('createWorkOrder', () => {
    it('POSTs to /work_orders with body and returns res.data', async () => {
      const fakeData = {
        id: 1,
        external_id: 'WO-1',
        status: 'submitted',
        ...createParams,
        handle_remark: '',
      }
      mockedRequest.post.mockResolvedValueOnce({ data: fakeData })

      const result = await createWorkOrder(createParams)

      expect(mockedRequest.post).toHaveBeenCalledWith('/work_orders', createParams)
      expect(result).toEqual(fakeData)
    })
  })

  describe('getWorkOrderDetail', () => {
    it('GETs /work_orders/:id with numeric id', async () => {
      const fakeData = { id: 42, external_id: 'WO-42', status: 'submitted' }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })

      const result = await getWorkOrderDetail(42)

      expect(mockedRequest.get).toHaveBeenCalledWith('/work_orders/42')
      expect(result).toEqual(fakeData)
    })

    it('GETs /work_orders/:id with string id', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: {} })
      await getWorkOrderDetail('abc')
      expect(mockedRequest.get).toHaveBeenCalledWith('/work_orders/abc')
    })
  })

  describe('replyWorkOrder', () => {
    it('PUTs handle_remark to /work_orders/:id/reply', async () => {
      const fakeData = { id: 7, status: 'processed', handle_remark: '已处理' }
      mockedRequest.put.mockResolvedValueOnce({ data: fakeData })

      const result = await replyWorkOrder(7, { handle_remark: '已处理' })

      expect(mockedRequest.put).toHaveBeenCalledWith('/work_orders/7/reply', {
        handle_remark: '已处理',
      })
      expect(result).toEqual(fakeData)
    })
  })
})
