import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'

const { mockRouterPush, mockElMessage, mockLoginApi, mockGetMyPermissions } = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockLoginApi: vi.fn(),
  mockGetMyPermissions: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
}))

vi.mock('@element-plus/icons-vue', () => ({
  User: defineComponent({ name: 'User', render: () => h('span', '👤') }),
  Lock: defineComponent({ name: 'Lock', render: () => h('span', '🔒') }),
}))

vi.mock('@/api/auth', () => ({
  login: mockLoginApi,
}))

vi.mock('@/api/system', () => ({
  getMyPermissions: mockGetMyPermissions,
}))

vi.mock('@/router', () => ({
  getDefaultPath: vi.fn((role: string) => `/default/${role}`),
}))

import Login from '@/pages/login.vue'
import { useAuthStore } from '@/stores/auth'

const stubs = {
  ElForm: {
    name: 'ElForm',
    props: ['model', 'labelWidth', 'size', 'rules'],
    emits: ['validate'],
    setup(_, { expose }) {
      expose({ validate: () => Promise.resolve() })
    },
    template: '<form class="el-form-stub"><slot></slot></form>',
  },
  ElFormItem: {
    name: 'ElFormItem',
    props: ['prop'],
    template: '<div class="el-form-item-stub"><slot></slot></div>',
  },
  ElInput: {
    name: 'ElInput',
    props: ['modelValue', 'placeholder', 'type', 'prefixIcon', 'clearable', 'showPassword'],
    emits: ['update:modelValue', 'keyup'],
    template:
      '<input class="el-input-stub" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
  ElButton: {
    name: 'ElButton',
    props: ['type', 'loading'],
    emits: ['click'],
    template:
      '<button class="el-button-stub" :disabled="loading" @click="$emit(\'click\')"><slot></slot></button>',
  },
}

describe('login', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    setActivePinia(createPinia())
    mockGetMyPermissions.mockResolvedValue([])
  })

  it('renders 欢迎登录 title', () => {
    const wrapper = mount(Login, { global: { stubs } })
    expect(wrapper.text()).toContain('欢迎登录')
  })

  it('renders form subtitle', () => {
    const wrapper = mount(Login, { global: { stubs } })
    expect(wrapper.text()).toContain('请输入您的账号信息')
  })

  it('renders username input with placeholder', () => {
    const wrapper = mount(Login, { global: { stubs } })
    const inputs = wrapper.findAll('input')
    expect(inputs.length).toBeGreaterThanOrEqual(2)
  })

  it('renders 登 录 button', () => {
    const wrapper = mount(Login, { global: { stubs } })
    expect(wrapper.text()).toContain('登 录')
  })

  it('login button is not loading initially', () => {
    const wrapper = mount(Login, { global: { stubs } })
    const btn = wrapper.find('button')
    expect(btn.attributes('disabled')).toBeUndefined()
  })

  it('successful login sets auth and redirects', async () => {
    mockLoginApi.mockResolvedValueOnce({
      access_token: 'tok123',
      token_type: 'bearer',
      role: 'admin',
      dept: 'aftersale',
    })
    mockGetMyPermissions.mockResolvedValueOnce(['/workbench/admin/dashboard'])

    const wrapper = mount(Login, { global: { stubs } })
    const authStore = useAuthStore()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('admin')
    await inputs[1].setValue('123456')

    const btn = wrapper.find('button')
    await btn.trigger('click')

    expect(mockLoginApi).toHaveBeenCalledWith({ username: 'admin', password: '123456' })
    expect(authStore.token).toBe('tok123')
    expect(authStore.role).toBe('admin')
    expect(mockElMessage.success).toHaveBeenCalledWith('登录成功')
  })

  it('failed login does not set auth', async () => {
    mockLoginApi.mockRejectedValueOnce(new Error('invalid credentials'))

    const wrapper = mount(Login, { global: { stubs } })
    const authStore = useAuthStore()

    const inputs = wrapper.findAll('input')
    await inputs[0].setValue('wrong')
    await inputs[1].setValue('wrong')

    const btn = wrapper.find('button')
    await btn.trigger('click')

    expect(mockLoginApi).toHaveBeenCalled()
    expect(authStore.token).toBe('')
  })
})
