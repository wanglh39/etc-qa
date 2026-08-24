import { describe, it, expect, vi, beforeEach } from 'vitest'
import request from '@/utils/request'
import { queryQA, getAsrHealth } from '@/api/workbench'

vi.mock('@/utils/request')

const mockedRequest = vi.mocked(request, true)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('api/workbench', () => {
  describe('queryQA', () => {
    it('POSTs question to /query and returns res.data', async () => {
      const fakeData = {
        query: '怎么退费',
        standardized_query: '退费流程',
        confidence: 'high',
        candidates: [],
        total_candidates: 0,
      }
      mockedRequest.post.mockResolvedValueOnce({ data: fakeData })

      const result = await queryQA({ question: '怎么退费' })

      expect(mockedRequest.post).toHaveBeenCalledWith('/query', { question: '怎么退费' })
      expect(result).toEqual(fakeData)
    })

    it('POSTs with category_l1 when provided', async () => {
      mockedRequest.post.mockResolvedValueOnce({ data: {} })
      await queryQA({ question: '退费', category_l1: '售后' })
      expect(mockedRequest.post).toHaveBeenCalledWith('/query', {
        question: '退费',
        category_l1: '售后',
      })
    })
  })

  describe('getAsrHealth', () => {
    it('GETs /asr/health and returns res.data', async () => {
      const fakeData = { loaded: true, model: 'fun-asr-nano', device: 'cpu', finetuned: false }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })

      const result = await getAsrHealth()

      expect(mockedRequest.get).toHaveBeenCalledWith('/asr/health')
      expect(result).toEqual(fakeData)
    })

    it('returns unloaded state correctly', async () => {
      const fakeData = { loaded: false }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })
      const result = await getAsrHealth()
      expect(result).toEqual({ loaded: false })
    })
  })
})
