import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const mockElMessage = {
  success: vi.fn(),
  warning: vi.fn(),
  error: vi.fn(),
  info: vi.fn(),
}

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
}))

const mockAuthStore = {
  token: '',
  clearAuth: vi.fn(),
}

vi.mock('@/stores/auth', () => ({
  useAuthStore: () => mockAuthStore,
}))

let requestInterceptor: (config: any) => any
let responseErrorInterceptor: (err: any) => any

const mockAxiosInstance = {
  interceptors: {
    request: {
      use: vi.fn((cb: any) => {
        requestInterceptor = cb
      }),
    },
    response: {
      use: vi.fn((_success: any, error: any) => {
        responseErrorInterceptor = error
      }),
    },
  },
  get: vi.fn(),
  post: vi.fn(),
  put: vi.fn(),
  delete: vi.fn(),
}

vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => mockAxiosInstance),
  },
}))

beforeEach(() => {
  vi.clearAllMocks()
  mockAuthStore.token = ''
})

describe('utils/request interceptors', () => {
  it('request interceptor adds Bearer token when token exists', async () => {
    await import('@/utils/request')
    mockAuthStore.token = 'mytoken123'
    const config = { headers: {} }
    const result = requestInterceptor(config)
    expect(result.headers.Authorization).toBe('Bearer mytoken123')
  })

  it('request interceptor does not add Authorization when no token', async () => {
    await import('@/utils/request')
    mockAuthStore.token = ''
    const config = { headers: {} }
    const result = requestInterceptor(config)
    expect(result.headers.Authorization).toBeUndefined()
  })

  it('401 response clears auth and redirects to /login', async () => {
    await import('@/utils/request')
    const err = { response: { status: 401, data: { detail: 'token expired' } } }
    const originalHref = window.location.href
    Object.defineProperty(window, 'location', {
      value: { href: originalHref },
      writable: true,
    })

    await expect(responseErrorInterceptor(err)).rejects.toBe(err)
    expect(mockAuthStore.clearAuth).toHaveBeenCalledTimes(1)
    expect(mockElMessage.warning).toHaveBeenCalledWith('登录已失效，请重新登录')
    expect(window.location.href).toBe('/login')
  })

  it('403 response shows permission error with detail', async () => {
    await import('@/utils/request')
    const err = { response: { status: 403, data: { detail: '无权操作' } } }
    await expect(responseErrorInterceptor(err)).rejects.toBe(err)
    expect(mockElMessage.error).toHaveBeenCalledWith('无权操作')
  })

  it('403 response shows default message when no detail', async () => {
    await import('@/utils/request')
    const err = { response: { status: 403, data: {} } }
    await expect(responseErrorInterceptor(err)).rejects.toBe(err)
    expect(mockElMessage.error).toHaveBeenCalledWith('权限不足，无法执行此操作')
  })

  it('500 response shows server error with detail', async () => {
    await import('@/utils/request')
    const err = { response: { status: 500, data: { detail: 'DB down' } } }
    await expect(responseErrorInterceptor(err)).rejects.toBe(err)
    expect(mockElMessage.error).toHaveBeenCalledWith('DB down')
  })

  it('502 response shows default server error message', async () => {
    await import('@/utils/request')
    const err = { response: { status: 502, data: {} } }
    await expect(responseErrorInterceptor(err)).rejects.toBe(err)
    expect(mockElMessage.error).toHaveBeenCalledWith('服务器内部错误，请稍后重试')
  })

  it('400 response shows generic error with detail', async () => {
    await import('@/utils/request')
    const err = { response: { status: 400, data: { detail: 'bad request' } } }
    await expect(responseErrorInterceptor(err)).rejects.toBe(err)
    expect(mockElMessage.error).toHaveBeenCalledWith('bad request')
  })

  it('400 response shows default generic message when no detail', async () => {
    await import('@/utils/request')
    const err = { response: { status: 400, data: {} } }
    await expect(responseErrorInterceptor(err)).rejects.toBe(err)
    expect(mockElMessage.error).toHaveBeenCalledWith('操作请求出错')
  })

  it('network error (no response) shows generic message', async () => {
    await import('@/utils/request')
    const err = { message: 'Network Error' }
    await expect(responseErrorInterceptor(err)).rejects.toBe(err)
    expect(mockElMessage.error).toHaveBeenCalledWith('操作请求出错')
  })
})

describe('utils/request mock data', () => {
  it('mockUserList has 3 users', async () => {
    const { mockUserList } = await import('@/utils/request')
    expect(mockUserList).toHaveLength(3)
    expect(mockUserList[0]).toHaveProperty('userId')
  })

  it('mockPendingList has 4 pending items with required fields', async () => {
    const { mockPendingList } = await import('@/utils/request')
    expect(mockPendingList).toHaveLength(4)
    expect(mockPendingList[0]).toHaveProperty('orderId')
    expect(mockPendingList[0]).toHaveProperty('question')
    expect(mockPendingList[0]).toHaveProperty('confidence')
    expect(mockPendingList[0]).toHaveProperty('submitTime')
  })

  it('mockCategoryTree has 3 top-level categories', async () => {
    const { mockCategoryTree } = await import('@/utils/request')
    expect(mockCategoryTree).toHaveLength(3)
    expect(mockCategoryTree[0].children).toHaveLength(2)
    expect(mockCategoryTree[2].children).toBeUndefined()
  })

  it('mockKnowledgeList has 3 knowledge items', async () => {
    const { mockKnowledgeList } = await import('@/utils/request')
    expect(mockKnowledgeList).toHaveLength(3)
    expect(mockKnowledgeList[0]).toHaveProperty('ID')
    expect(mockKnowledgeList[0]).toHaveProperty('questionTitle')
    expect(mockKnowledgeList[0]).toHaveProperty('belongClass')
    expect(mockKnowledgeList[0]).toHaveProperty('status')
  })

  it('mockDispatch returns correct data for /workbench/users', async () => {
    const { mockDispatch, mockUserList } = await import('@/utils/request')
    const result = await mockDispatch('/workbench/users')
    expect(result.data).toBe(mockUserList)
  })

  it('mockDispatch returns correct data for /knowledge/list', async () => {
    const { mockDispatch, mockKnowledgeList } = await import('@/utils/request')
    const result = await mockDispatch('/knowledge/list')
    expect(result.data).toBe(mockKnowledgeList)
  })

  it('mockDispatch returns correct data for /knowledge/categoryTree', async () => {
    const { mockDispatch, mockCategoryTree } = await import('@/utils/request')
    const result = await mockDispatch('/knowledge/categoryTree')
    expect(result.data).toBe(mockCategoryTree)
  })

  it('mockDispatch returns correct data for /audit/pending', async () => {
    const { mockDispatch, mockPendingList } = await import('@/utils/request')
    const result = await mockDispatch('/audit/pending')
    expect(result.data).toBe(mockPendingList)
  })
})
