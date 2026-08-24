import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const { mockRouterPush, mockElMessage, mockElMessageBox, mockElNotification } = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(() => Promise.resolve()),
  },
  mockElNotification: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush, back: vi.fn() }),
  useRoute: () => ({ query: {} }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: mockElMessageBox,
  ElNotification: mockElNotification,
}))

vi.mock('@element-plus/icons-vue', () => ({
  ...iconStubs,
}))

import AuditIndex from '@/pages/audit/index.vue'

const PageLayoutStub = {
  name: 'PageLayout',
  props: ['pageTitle'],
  template:
    '<div class="page-layout-stub"><div class="page-title">{{ pageTitle }}</div><div class="page-actions"><slot name="actions"></slot></div><div class="page-content"><slot></slot></div></div>',
}

const stubs = {
  ...commonStubs,
  ...iconStubs,
  PageLayout: PageLayoutStub,
  ElScrollbar: {
    name: 'ElScrollbar',
    props: ['height'],
    template: '<div class="el-scrollbar-stub"><slot></slot></div>',
  },
}

describe('auditIndex', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  it('renders 智能办结问题 title', () => {
    const wrapper = mount(AuditIndex, { global: { stubs } })
    expect(wrapper.text()).toContain('智能办结问题')
  })

  it('renders 刷新数据 button', () => {
    const wrapper = mount(AuditIndex, { global: { stubs } })
    expect(wrapper.text()).toContain('刷新数据')
  })

  it('renders 一键采用回复 button', () => {
    const wrapper = mount(AuditIndex, { global: { stubs } })
    expect(wrapper.text()).toContain('一键采用回复')
  })

  it('renders 标记无效 button', () => {
    const wrapper = mount(AuditIndex, { global: { stubs } })
    expect(wrapper.text()).toContain('标记无效')
  })

  it('renders 创建CRM工单 button', () => {
    const wrapper = mount(AuditIndex, { global: { stubs } })
    expect(wrapper.text()).toContain('创建CRM工单')
  })

  it('renders 用户列表 header', () => {
    const wrapper = mount(AuditIndex, { global: { stubs } })
    expect(wrapper.text()).toContain('用户列表')
  })

  it('renders 20 user items', () => {
    const wrapper = mount(AuditIndex, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('U0001')
    expect(text).toContain('U0005')
    expect(text).toContain('U00020')
  })

  it('renders textarea with question content', () => {
    const wrapper = mount(AuditIndex, { global: { stubs } })
    const inputs = wrapper.findAll('input')
    const values = inputs.map((i) => i.attributes('value'))
    expect(values.some((v) => v && v.includes('客户来电询问商品质保时长'))).toBe(true)
  })
})
