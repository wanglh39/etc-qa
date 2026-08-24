import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

const { mockRouterPush } = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
}))

vi.mock('@/router', () => ({
  getDefaultPath: vi.fn((role: string) => `/default/${role}`),
}))

import NotFound from '@/pages/NotFound.vue'
import { useAuthStore } from '@/stores/auth'

const stubs = {
  ElButton: {
    name: 'ElButton',
    props: ['type'],
    emits: ['click'],
    template: '<button @click="$emit(\'click\')"><slot></slot></button>',
  },
}

describe('NotFound', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  it('renders 404 code', () => {
    const wrapper = mount(NotFound, { global: { stubs } })
    expect(wrapper.text()).toContain('404')
  })

  it('renders error description', () => {
    const wrapper = mount(NotFound, { global: { stubs } })
    expect(wrapper.text()).toContain('页面不存在或已被移除')
  })

  it('renders 返回首页 button', () => {
    const wrapper = mount(NotFound, { global: { stubs } })
    expect(wrapper.text()).toContain('返回首页')
  })

  it('goHome pushes to default path for current role', async () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    const wrapper = mount(NotFound, { global: { stubs } })
    const btn = wrapper.find('button')
    await btn.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/default/admin')
  })

  it('goHome works for service role', async () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'service', '')
    const wrapper = mount(NotFound, { global: { stubs } })
    const btn = wrapper.find('button')
    await btn.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/default/service')
  })
})
