import { describe, it, expect, vi, beforeEach } from 'vitest'
import request from '@/utils/request'
import { login, verifyToken, impersonate } from '@/api/auth'

vi.mock('@/utils/request')

const mockedRequest = vi.mocked(request, true)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('api/auth', () => {
  describe('login', () => {
    it('POSTs to /auth/login and returns res.data', async () => {
      const payload = { username: 'admin', password: '123456' }
      const fakeData = {
        access_token: 'tok',
        token_type: 'bearer',
        role: 'admin',
        dept: 'aftersale',
      }
      mockedRequest.post.mockResolvedValueOnce({ data: fakeData })

      const result = await login(payload)

      expect(mockedRequest.post).toHaveBeenCalledWith('/auth/login', payload)
      expect(result).toEqual(fakeData)
    })

    it('propagates rejection on network error', async () => {
      mockedRequest.post.mockRejectedValueOnce(new Error('network'))
      await expect(login({ username: 'x', password: 'y' })).rejects.toThrow('network')
    })
  })

  describe('verifyToken', () => {
    it('GETs /auth/verify and returns res.data', async () => {
      const fakeData = { username: 'admin', role: 'admin', dept: 'aftersale' }
      mockedRequest.get.mockResolvedValueOnce({ data: fakeData })

      const result = await verifyToken()

      expect(mockedRequest.get).toHaveBeenCalledWith('/auth/verify')
      expect(result).toEqual(fakeData)
    })
  })

  describe('impersonate', () => {
    it('POSTs target_role to /auth/impersonate', async () => {
      const fakeData = {
        access_token: 't2',
        token_type: 'bearer',
        role: 'service',
        dept: '',
        username: 'svc',
      }
      mockedRequest.post.mockResolvedValueOnce({ data: fakeData })

      const result = await impersonate('service')

      expect(mockedRequest.post).toHaveBeenCalledWith('/auth/impersonate', {
        target_role: 'service',
      })
      expect(result).toEqual(fakeData)
    })

    it('encodes different roles correctly', async () => {
      mockedRequest.post.mockResolvedValueOnce({ data: {} })
      await impersonate('dept')
      expect(mockedRequest.post).toHaveBeenCalledWith('/auth/impersonate', { target_role: 'dept' })
    })
  })
})
