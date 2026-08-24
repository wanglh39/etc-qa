import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const { mockRouterReplace, mockElMessage, mockImpersonate, mockGetRoleList } = vi.hoisted(() => ({
  mockRouterReplace: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockImpersonate: vi.fn(),
  mockGetRoleList: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: mockRouterReplace }),
  useRoute: () => ({ path: '/' }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()), alert: vi.fn(() => Promise.resolve()) },
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => {
  const s = (n: string) => defineComponent({ name: n, render: () => h('span') })
  return {
    Setting: s('Setting'),
    Monitor: s('Monitor'),
    Service: s('Service'),
    Ticket: s('Ticket'),
    Location: s('Location'),
  }
})

vi.mock('@/api/auth', () => ({
  impersonate: mockImpersonate,
}))

vi.mock('@/api/system', () => ({
  getRoleList: mockGetRoleList,
}))

vi.mock('@/utils/roleColor', () => ({
  roleColor: vi.fn(() => '#1677FF'),
}))

vi.mock('@/config/pages', () => ({
  ALL_PAGES: [
    { path: '/workbench/admin/dashboard', label: '数据看板', icon: {}, group: '' },
    { path: '/workbench/admin/account', label: '账号管理', icon: {}, group: '系统管理' },
    { path: '/service', label: '客服工作台', icon: {}, group: '' },
  ],
  getPageLabel: vi.fn((p: string) => p),
}))

import Impersonate from '@/pages/system/impersonate.vue'
import { useAuthStore } from '@/stores/auth'

const roleList = [
  {
    id: 1,
    role_key: 'superadmin',
    role_name: '超级管理员',
    description: '系统管理',
    permissions: ['/workbench/admin/account'],
  },
  {
    id: 2,
    role_key: 'admin',
    role_name: '业务管理员',
    description: '审核+知识库',
    permissions: ['/workbench/admin/dashboard'],
  },
  {
    id: 3,
    role_key: 'service',
    role_name: '客服',
    description: '客服工作台',
    permissions: ['/service'],
  },
]

describe('Impersonate', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetRoleList.mockResolvedValue(roleList)
    mockImpersonate.mockResolvedValue({
      access_token: 'imp-tok',
      token_type: 'bearer',
      role: 'admin',
      dept: 'aftersale',
      username: 'admin',
    })
  })

  const mountImpersonate = () =>
    mount(Impersonate, { global: { stubs: { ...commonStubs, ...iconStubs } } })

  it('渲染模拟登录说明提示', async () => {
    const wrapper = mountImpersonate()
    await flushPromises()
    const alert = wrapper.findComponent({ name: 'ElAlert' })
    expect(alert.props('title')).toBe('模拟登录说明')
    expect(wrapper.text()).toContain('选择目标角色后')
  })

  it('渲染可访问页面标签', async () => {
    const wrapper = mountImpersonate()
    await flushPromises()
    expect(wrapper.text()).toContain('可访问页面：')
  })

  it('角色卡片排除superadmin', async () => {
    const wrapper = mountImpersonate()
    await flushPromises()
    const cards = wrapper.findAll('.role-card')
    expect(cards.length).toBe(2)
  })

  it('每个角色卡片含模拟登录按钮', async () => {
    const wrapper = mountImpersonate()
    await flushPromises()
    const buttons = wrapper.findAll('button').filter((b) => b.text().includes('模拟登录'))
    expect(buttons.length).toBe(2)
  })

  it('初始挂载调用getRoleList', async () => {
    mountImpersonate()
    await flushPromises()
    expect(mockGetRoleList).toHaveBeenCalled()
  })

  it('点击模拟登录调用impersonate并切换身份', async () => {
    const wrapper = mountImpersonate()
    await flushPromises()
    const authStore = useAuthStore()
    authStore.setAuth('super-tok', 'superadmin', '', 'superadmin')
    const btn = wrapper.findAll('button').find((b) => b.text().includes('模拟登录'))
    await btn!.trigger('click')
    await flushPromises()
    expect(mockImpersonate).toHaveBeenCalled()
    expect(authStore.token).toBe('imp-tok')
    expect(mockRouterReplace).toHaveBeenCalled()
  })

  it('渲染角色描述信息', async () => {
    const wrapper = mountImpersonate()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('业务管理员')
    expect(text).toContain('客服')
  })

  it('模拟登录成功提示具体角色名', async () => {
    const wrapper = mountImpersonate()
    await flushPromises()
    const authStore = useAuthStore()
    authStore.setAuth('super-tok', 'superadmin', '', 'superadmin')
    const btn = wrapper.findAll('button').find((b) => b.text().includes('模拟登录'))
    await btn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.success).toHaveBeenCalledWith('已切换为业务管理员身份')
  })

  it('模拟登录后authStore角色与身份更新', async () => {
    const wrapper = mountImpersonate()
    await flushPromises()
    const authStore = useAuthStore()
    authStore.setAuth('super-tok', 'superadmin', '', 'superadmin')
    const btn = wrapper.findAll('button').find((b) => b.text().includes('模拟登录'))
    await btn!.trigger('click')
    await flushPromises()
    expect(authStore.role).toBe('admin')
    expect(authStore.dept).toBe('aftersale')
    expect(authStore.username).toBe('admin')
    expect(authStore.isImpersonating).toBe(true)
  })

  it('模拟登录失败提示错误', async () => {
    mockImpersonate.mockRejectedValue(new Error('fail'))
    const wrapper = mountImpersonate()
    await flushPromises()
    const authStore = useAuthStore()
    authStore.setAuth('super-tok', 'superadmin', '', 'superadmin')
    const btn = wrapper.findAll('button').find((b) => b.text().includes('模拟登录'))
    await btn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('模拟登录失败')
  })

  it('点击客服角色模拟登录调用impersonate', async () => {
    mockImpersonate.mockResolvedValue({
      access_token: 'svc-tok',
      token_type: 'bearer',
      role: 'service',
      dept: '',
      username: 'service',
    })
    const wrapper = mountImpersonate()
    await flushPromises()
    const authStore = useAuthStore()
    authStore.setAuth('super-tok', 'superadmin', '', 'superadmin')
    const btns = wrapper.findAll('button').filter((b) => b.text().includes('模拟登录'))
    await btns[1].trigger('click')
    await flushPromises()
    expect(mockImpersonate).toHaveBeenCalledWith('service')
    expect(mockElMessage.success).toHaveBeenCalledWith('已切换为客服身份')
  })

  it('加载角色失败提示错误', async () => {
    mockGetRoleList.mockRejectedValue(new Error('fail'))
    const wrapper = mountImpersonate()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载角色列表失败')
  })
})
