import { describe, it, expect, vi, beforeEach } from 'vitest'
import request from '@/utils/request'
import {
  getQAList,
  searchQA,
  getQADetail,
  addQA,
  updateQAStatus,
  deleteQA,
  getCategories,
  createCategory,
  updateCategory,
  deleteCategory,
} from '@/api/knowledge'

vi.mock('@/utils/request')

const mockedRequest = vi.mocked(request, true)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('api/knowledge', () => {
  describe('getQAList', () => {
    it('GETs /qa/list with params', async () => {
      const fakeData = { items: [], total: 0, page: 1, page_size: 20 }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })

      const result = await getQAList({
        page: 1,
        page_size: 20,
        category_l1: '售后',
        status: 'active',
      })

      expect(mockedRequest.get).toHaveBeenCalledWith('/qa/list', {
        params: { page: 1, page_size: 20, category_l1: '售后', status: 'active' },
      })
      expect(result).toEqual(fakeData)
    })
  })

  describe('searchQA', () => {
    it('POSTs search criteria to /qa/search', async () => {
      const fakeData = { items: [], total: 0, page: 1, page_size: 20 }
      mockedRequest.post.mockResolvedValueOnce({ data: fakeData })

      const result = await searchQA({
        keyword: '退费',
        category_l1: '售后',
        page: 1,
        page_size: 10,
      })

      expect(mockedRequest.post).toHaveBeenCalledWith('/qa/search', {
        keyword: '退费',
        category_l1: '售后',
        page: 1,
        page_size: 10,
      })
      expect(result).toEqual(fakeData)
    })
  })

  describe('getQADetail', () => {
    it('GETs /qa/:id', async () => {
      const fakeData = {
        id: 5,
        question: 'q',
        answer: 'a',
        category_l1: 'c1',
        category_l2: 'c2',
        internal_process: '',
        feedback_dept: '',
        status: 'active',
      }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })

      const result = await getQADetail(5)

      expect(mockedRequest.get).toHaveBeenCalledWith('/qa/5')
      expect(result).toEqual(fakeData)
    })
  })

  describe('addQA', () => {
    it('POSTs to /add', async () => {
      const fakeData = { qa_id: 10, message: 'ok' }
      mockedRequest.post.mockResolvedValueOnce({ data: fakeData })

      const result = await addQA({ question: 'q', answer: 'a' })

      expect(mockedRequest.post).toHaveBeenCalledWith('/add', { question: 'q', answer: 'a' })
      expect(result).toEqual(fakeData)
    })
  })

  describe('updateQAStatus', () => {
    it('PUTs to /qa/status with qa_id and status', async () => {
      mockedRequest.put.mockResolvedValueOnce({ data: { ok: true } })
      await updateQAStatus(3, 'deprecated')
      expect(mockedRequest.put).toHaveBeenCalledWith('/qa/status', {
        qa_id: 3,
        status: 'deprecated',
      })
    })
  })

  describe('deleteQA', () => {
    it('DELETEs /qa/:id', async () => {
      mockedRequest.delete.mockResolvedValueOnce({ data: { ok: true } })
      await deleteQA(8)
      expect(mockedRequest.delete).toHaveBeenCalledWith('/qa/8')
    })
  })

  describe('getCategories', () => {
    it('GETs /categories', async () => {
      const fakeData = { categories: [{ id: 1, label: '售后' }] }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })
      const result = await getCategories()
      expect(mockedRequest.get).toHaveBeenCalledWith('/categories')
      expect(result).toEqual(fakeData)
    })
  })

  describe('createCategory', () => {
    it('POSTs to /categories', async () => {
      const fakeData = { id: 1, message: 'ok' }
      mockedRequest.post.mockResolvedValueOnce({ data: fakeData })
      const result = await createCategory({ label: '售后' })
      expect(mockedRequest.post).toHaveBeenCalledWith('/categories', { label: '售后' })
      expect(result).toEqual(fakeData)
    })
  })

  describe('updateCategory', () => {
    it('PUTs to /categories/:id', async () => {
      mockedRequest.put.mockResolvedValueOnce({ data: { id: 1, message: 'ok' } })
      await updateCategory(1, { label: '售后2' })
      expect(mockedRequest.put).toHaveBeenCalledWith('/categories/1', { label: '售后2' })
    })
  })

  describe('deleteCategory', () => {
    it('DELETEs /categories/:id', async () => {
      mockedRequest.delete.mockResolvedValueOnce({ data: { id: 1, message: 'ok' } })
      await deleteCategory(1)
      expect(mockedRequest.delete).toHaveBeenCalledWith('/categories/1')
    })
  })
})
