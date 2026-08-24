import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockRouterPush,
  mockRouterBack,
  mockElMessage,
  mockElMessageBox,
  mockElNotification,
  mockGetAuditHistory,
} = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockRouterBack: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(() => Promise.resolve()),
  },
  mockElNotification: vi.fn(),
  mockGetAuditHistory: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush, back: mockRouterBack }),
  useRoute: () => ({ query: {} }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: mockElMessageBox,
  ElNotification: mockElNotification,
}))

vi.mock('@element-plus/icons-vue', () => ({
  ...iconStubs,
  CircleClose: defineComponent({ name: 'CircleClose', render: () => h('span', 'CircleClose') }),
  Histogram: defineComponent({ name: 'Histogram', render: () => h('span', 'Histogram') }),
}))

vi.mock('@/api/audit', () => ({
  getAuditHistory: mockGetAuditHistory,
}))

import History from '@/pages/audit/history.vue'

const stubs = {
  ...commonStubs,
  ...iconStubs,
  CircleClose: defineComponent({ name: 'CircleClose', render: () => h('span', 'CircleClose') }),
  Histogram: defineComponent({ name: 'Histogram', render: () => h('span', 'Histogram') }),
  ElTableColumn: {
    name: 'ElTableColumn',
    props: ['type', 'width', 'prop', 'label', 'fixed'],
    template: '<div class="el-table-col-stub">{{ label }}</div>',
  },
}

describe('history', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    setActivePinia(createPinia())
    mockGetAuditHistory.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 20 })
  })

  it('renders 审核历史记录 title', () => {
    const wrapper = mount(History, { global: { stubs } })
    expect(wrapper.text()).toContain('审核历史记录')
  })

  it('renders 刷新 button', () => {
    const wrapper = mount(History, { global: { stubs } })
    expect(wrapper.text()).toContain('刷新')
  })

  it('renders KPI labels', () => {
    const wrapper = mount(History, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('总审核数')
    expect(text).toContain('入库通过')
    expect(text).toContain('已驳回')
    expect(text).toContain('通过率')
  })

  it('renders table column labels', () => {
    const wrapper = mount(History, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('审核编号')
    expect(text).toContain('审核问题')
    expect(text).toContain('标准化答案')
    expect(text).toContain('审核结果')
    expect(text).toContain('操作管理员')
    expect(text).toContain('审核时间')
  })

  it('renders pagination component', () => {
    const wrapper = mount(History, { global: { stubs } })
    expect(wrapper.find('.el-pagination-stub').exists()).toBe(true)
  })

  it('calls getAuditHistory on mount', () => {
    mount(History, { global: { stubs } })
    expect(mockGetAuditHistory).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  })

  it('displays computed KPI values after load', async () => {
    mockGetAuditHistory.mockResolvedValueOnce({
      items: [
        {
          id: 1,
          question: '质保多久',
          answer: '一年',
          result: 'pass',
          operator: 'admin',
          created_at: '2024-01-01',
        },
        {
          id: 2,
          question: '退货吗',
          answer: '',
          result: 'reject',
          operator: 'ops',
          created_at: '2024-01-02',
        },
      ],
      total: 2,
      page: 1,
      page_size: 20,
    })
    const wrapper = mount(History, { global: { stubs } })
    await flushPromises()
    const kpiValues = wrapper.findAll('.kpi-value')
    expect(kpiValues.length).toBe(4)
    expect(kpiValues[0].text()).toBe('2')
    expect(kpiValues[1].text()).toBe('1')
    expect(kpiValues[2].text()).toBe('1')
    expect(kpiValues[3].text()).toBe('50%')
  })

  it('shows error message on load failure', async () => {
    mockGetAuditHistory.mockRejectedValueOnce(new Error('fail'))
    mount(History, { global: { stubs } })
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载审核历史失败')
  })

  it('点击刷新按钮重新加载历史', async () => {
    const wrapper = mount(History, { global: { stubs } })
    await flushPromises()
    mockGetAuditHistory.mockClear()
    const refreshBtn = wrapper.findAll('button').find((b) => b.text() === '刷新')
    await refreshBtn!.trigger('click')
    await flushPromises()
    expect(mockGetAuditHistory).toHaveBeenCalledWith({ page: 1, page_size: 20 })
  })

  it('分页 current-change 切换到第2页带新页码', async () => {
    const wrapper = mount(History, { global: { stubs } })
    await flushPromises()
    mockGetAuditHistory.mockClear()
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    await pagination.vm.$emit('update:current-page', 2)
    await pagination.vm.$emit('current-change')
    await flushPromises()
    expect(mockGetAuditHistory).toHaveBeenLastCalledWith({ page: 2, page_size: 20 })
  })

  it('分页 size-change 改变每页条数', async () => {
    const wrapper = mount(History, { global: { stubs } })
    await flushPromises()
    mockGetAuditHistory.mockClear()
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    await pagination.vm.$emit('update:page-size', 50)
    await pagination.vm.$emit('size-change')
    await flushPromises()
    expect(mockGetAuditHistory).toHaveBeenLastCalledWith({ page: 1, page_size: 50 })
  })

  it('刷新失败时提示错误', async () => {
    const wrapper = mount(History, { global: { stubs } })
    await flushPromises()
    mockGetAuditHistory.mockRejectedValueOnce(new Error('fail'))
    const refreshBtn = wrapper.findAll('button').find((b) => b.text() === '刷新')
    await refreshBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载审核历史失败')
  })
})
