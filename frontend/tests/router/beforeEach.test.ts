import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

const { mockCreateRouter, mockBeforeEach, mockElMessage } = vi.hoisted(() => ({
  mockCreateRouter: vi.fn(),
  mockBeforeEach: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
}))

vi.mock('vue-router', () => ({
  createRouter: (...args: any[]) => {
    const router = mockCreateRouter(...args)
    router.beforeEach = mockBeforeEach
    return router
  },
  createWebHistory: vi.fn(),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
}))

let beforeEachGuard: any = null

async function setupRouter() {
  vi.resetModules()
  mockBeforeEach.mockImplementation((cb: any) => {
    beforeEachGuard = cb
  })
  mockCreateRouter.mockReturnValue({
    beforeEach: mockBeforeEach,
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    options: { routes: [] },
  })
  await import('@/router/index')
}

async function runGuard(toPath: string, toMeta: any = {}) {
  const to = { path: toPath, meta: toMeta }
  const from = { path: '/' }
  const next = vi.fn()
  await beforeEachGuard(to, from, next)
  return next
}

function makeJWT(exp?: number): string {
  const header = btoa(JSON.stringify({ alg: 'HS256', typ: 'JWT' }))
  const payload = btoa(JSON.stringify({ exp, role: 'admin', dept: 'aftersale' }))
  return `${header}.${payload}.signature`
}

describe('router beforeEach guard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('allows navigation to /login without checks', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    const next = await runGuard('/login')
    expect(next).toHaveBeenCalledWith()
  })

  it('redirects to /login when no token', async () => {
    await setupRouter()
    const next = await runGuard('/workbench/admin/dashboard')
    expect(next).toHaveBeenCalledWith('/login')
    expect(mockElMessage.warning).toHaveBeenCalledWith('请先登录系统')
  })

  it('redirects to /login when token expired', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const expiredToken = makeJWT(Math.floor(Date.now() / 1000) - 3600)
    const authStore = useAuthStore()
    authStore.setAuth(expiredToken, 'admin', '')
    const next = await runGuard('/workbench/admin/dashboard')
    expect(next).toHaveBeenCalledWith('/login')
    expect(mockElMessage.warning).toHaveBeenCalledWith('登录已过期，请重新登录')
  })

  it('redirects to /login when token is invalid JWT', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const authStore = useAuthStore()
    authStore.setAuth('invalid.token.format', 'admin', '')
    const next = await runGuard('/workbench/admin/dashboard')
    expect(next).toHaveBeenCalledWith('/login')
    expect(mockElMessage.warning).toHaveBeenCalledWith('登录信息异常，请重新登录')
  })

  it('redirects to /login when token verify fetch fails', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const validToken = makeJWT(Math.floor(Date.now() / 1000) + 3600)
    const authStore = useAuthStore()
    authStore.setAuth(validToken, 'admin', '')
    global.fetch = vi.fn().mockRejectedValue(new Error('network'))
    const next = await runGuard('/workbench/admin/dashboard')
    expect(next).toHaveBeenCalledWith('/login')
    expect(mockElMessage.warning).toHaveBeenCalledWith('无法连接服务器，请重新登录')
  })

  it('redirects to /login when token verify returns non-ok', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const validToken = makeJWT(Math.floor(Date.now() / 1000) + 3600)
    const authStore = useAuthStore()
    authStore.setAuth(validToken, 'admin', '')
    global.fetch = vi.fn().mockResolvedValue({ ok: false })
    const next = await runGuard('/workbench/admin/dashboard')
    expect(next).toHaveBeenCalledWith('/login')
    expect(mockElMessage.warning).toHaveBeenCalledWith('登录信息已失效，请重新登录')
  })

  it('allows access when token verify succeeds and role matches', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const validToken = makeJWT(Math.floor(Date.now() / 1000) + 3600)
    const authStore = useAuthStore()
    authStore.setAuth(validToken, 'admin', '')
    global.fetch = vi.fn().mockResolvedValue({ ok: true })
    const next = await runGuard('/workbench/admin/dashboard', { roleAuth: 'admin' })
    expect(next).toHaveBeenCalledWith()
  })

  it('superadmin bypasses role check', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const validToken = makeJWT(Math.floor(Date.now() / 1000) + 3600)
    const authStore = useAuthStore()
    authStore.setAuth(validToken, 'superadmin', '')
    global.fetch = vi.fn().mockResolvedValue({ ok: true })
    const next = await runGuard('/workbench/admin/account', { roleAuth: 'superadmin' })
    expect(next).toHaveBeenCalledWith()
  })

  it('redirects when role not in roleAuth list', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const validToken = makeJWT(Math.floor(Date.now() / 1000) + 3600)
    const authStore = useAuthStore()
    authStore.setAuth(validToken, 'service', '')
    global.fetch = vi.fn().mockResolvedValue({ ok: true })
    const next = await runGuard('/workbench/admin/dashboard', { roleAuth: 'admin' })
    expect(next).toHaveBeenCalledWith('/service')
    expect(mockElMessage.warning).toHaveBeenCalledWith('无权访问该页面')
  })

  it('allows access when role in comma-separated roleAuth', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const validToken = makeJWT(Math.floor(Date.now() / 1000) + 3600)
    const authStore = useAuthStore()
    authStore.setAuth(validToken, 'ops', '')
    global.fetch = vi.fn().mockResolvedValue({ ok: true })
    const next = await runGuard('/workbench/admin/dashboard', { roleAuth: 'admin,ops' })
    expect(next).toHaveBeenCalledWith()
  })

  it('allows access when roleAuth is all', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const validToken = makeJWT(Math.floor(Date.now() / 1000) + 3600)
    const authStore = useAuthStore()
    authStore.setAuth(validToken, 'service', '')
    global.fetch = vi.fn().mockResolvedValue({ ok: true })
    const next = await runGuard('/service', { roleAuth: 'all' })
    expect(next).toHaveBeenCalledWith()
  })

  it('allows access when no roleAuth set', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const validToken = makeJWT(Math.floor(Date.now() / 1000) + 3600)
    const authStore = useAuthStore()
    authStore.setAuth(validToken, 'admin', '')
    global.fetch = vi.fn().mockResolvedValue({ ok: true })
    const next = await runGuard('/some/path', {})
    expect(next).toHaveBeenCalledWith()
  })

  it('allows access via permissions even when role not in roleAuth', async () => {
    await setupRouter()
    const { useAuthStore } = await import('@/stores/auth')
    const validToken = makeJWT(Math.floor(Date.now() / 1000) + 3600)
    const authStore = useAuthStore()
    authStore.setAuth(validToken, 'custom', '')
    authStore.setPermissions(['/custom/page'])
    global.fetch = vi.fn().mockResolvedValue({ ok: true })
    const next = await runGuard('/custom/page', { roleAuth: 'admin' })
    expect(next).toHaveBeenCalledWith()
  })
})
