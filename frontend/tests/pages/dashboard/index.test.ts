import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const { mockUseAuthStore, mockElMessage, mockGetStats, mockGetStatsTrend, mockGetMyPermissions } =
  vi.hoisted(() => ({
    mockUseAuthStore: vi.fn(() => ({
      username: 'admin',
      role: 'admin',
      roleText: '业务管理员',
      permissions: [],
    })),
    mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
    mockGetStats: vi.fn(),
    mockGetStatsTrend: vi.fn(),
    mockGetMyPermissions: vi.fn(),
  }))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ path: '/' }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()), alert: vi.fn(() => Promise.resolve()) },
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => ({
  ...iconStubs,
  Message: defineComponent({ name: 'Message', render: () => h('span') }),
  Tickets: defineComponent({ name: 'Tickets', render: () => h('span') }),
}))

vi.mock('echarts', () => {
  const init = vi.fn(() => ({ setOption: vi.fn(), dispose: vi.fn() }))
  return { init, graphic: { LinearGradient: vi.fn() } }
})

vi.mock('@/api/dashboard', () => ({
  getStats: mockGetStats,
  getStatsTrend: mockGetStatsTrend,
}))

vi.mock('@/api/system', () => ({
  getMyPermissions: mockGetMyPermissions,
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: mockUseAuthStore,
}))

import DashboardIndex from '@/pages/dashboard/index.vue'

const StatisticCardStub = {
  name: 'StatisticCard',
  props: [
    'title',
    'value',
    'desc',
    'icon',
    'iconColor',
    'growth',
    'progress',
    'sparkline',
    'to',
    'alert',
  ],
  template:
    '<div class="stat-card-stub"><span class="stat-title">{{ title }}</span><span class="stat-value">{{ value }}</span></div>',
}

const stubs = {
  ...commonStubs,
  ...iconStubs,
  StatisticCard: StatisticCardStub,
  ElRadioButton: {
    name: 'ElRadioButton',
    props: ['value'],
    template: '<div class="el-radio-button-stub"><slot></slot></div>',
  },
}

const statsData = {
  qa_total: 100,
  qa_active: 80,
  qa_deprecated: 15,
  qa_archived: 5,
  work_order_total: 50,
  work_order_submitted: 10,
  work_order_processed: 30,
  category_stats: { 售后: 20, 产品: 30 },
}
const trendData = {
  dates: ['2024-01-01', '2024-01-02'],
  work_order_counts: [3, 5],
  qa_new_counts: [2, 4],
}

describe('dashboardIndex', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetStats.mockResolvedValue(statsData)
    mockGetStatsTrend.mockResolvedValue(trendData)
    mockGetMyPermissions.mockResolvedValue([])
  })

  const mountDashboard = () => mount(DashboardIndex, { global: { stubs } })

  it('渲染欢迎横幅描述文本', async () => {
    const wrapper = mountDashboard()
    await flushPromises()
    expect(wrapper.text()).toContain('欢迎使用智能客服话术系统数据看板')
  })

  it('渲染时间范围选择器 近7天 近30天 近90天', async () => {
    const wrapper = mountDashboard()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('近7天')
    expect(text).toContain('近30天')
    expect(text).toContain('近90天')
  })

  it('渲染刷新按钮', async () => {
    const wrapper = mountDashboard()
    await flushPromises()
    expect(wrapper.text()).toContain('刷新')
  })

  it('渲染4个KPI卡片标题', async () => {
    const wrapper = mountDashboard()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('知识库总数')
    expect(text).toContain('已激活知识')
    expect(text).toContain('待审核知识')
    expect(text).toContain('工单总数')
  })

  it('渲染图表卡片标题', async () => {
    const wrapper = mountDashboard()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('每日咨询趋势')
    expect(text).toContain('问题分类占比')
    expect(text).toContain('工单状态分布')
    expect(text).toContain('知识库状态分布')
  })

  it('挂载时调用 getStats 与 getStatsTrend', async () => {
    mountDashboard()
    await flushPromises()
    expect(mockGetStats).toHaveBeenCalled()
    expect(mockGetStatsTrend).toHaveBeenCalled()
  })

  it('挂载时调用 getMyPermissions', async () => {
    mountDashboard()
    await flushPromises()
    expect(mockGetMyPermissions).toHaveBeenCalled()
  })

  it('渲染KPI卡片数值', async () => {
    const wrapper = mountDashboard()
    await flushPromises()
    const titles = wrapper.findAll('.stat-title')
    const values = wrapper.findAll('.stat-value')
    expect(titles.length).toBe(4)
    expect(values[0].text()).toBe('100')
    expect(values[1].text()).toBe('80')
    expect(values[2].text()).toBe('15')
    expect(values[3].text()).toBe('50')
  })

  it('切换时间范围到30天调用 getStatsTrend(30)', async () => {
    const wrapper = mountDashboard()
    await flushPromises()
    mockGetStatsTrend.mockClear()
    const radio = wrapper.findComponent({ name: 'ElRadioGroup' })
    await radio.vm.$emit('update:modelValue', 30)
    await radio.vm.$emit('change')
    await flushPromises()
    expect(mockGetStatsTrend).toHaveBeenLastCalledWith(30)
  })

  it('点击刷新按钮重新加载 stats 与 trend', async () => {
    const wrapper = mountDashboard()
    await flushPromises()
    mockGetStats.mockClear()
    mockGetStatsTrend.mockClear()
    const refreshBtn = wrapper.findAll('button').find((b) => b.text() === '刷新')
    await refreshBtn!.trigger('click')
    await flushPromises()
    expect(mockGetStats).toHaveBeenCalled()
    expect(mockGetStatsTrend).toHaveBeenCalled()
  })

  it('getStats 失败时使用默认值不抛错', async () => {
    mockGetStats.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mountDashboard()
    await flushPromises()
    expect(mockElMessage.error).not.toHaveBeenCalled()
    const values = wrapper.findAll('.stat-value')
    expect(values[0].text()).toBe('0')
  })

  it('有权限时 KPI 卡片带跳转路径', async () => {
    mockGetMyPermissions.mockResolvedValueOnce([
      '/workbench/admin/knowledge',
      '/workbench/admin/auditList',
    ])
    const wrapper = mountDashboard()
    await flushPromises()
    const cards = wrapper.findAllComponents({ name: 'StatisticCard' })
    expect(cards[0].props('to')).toBe('/workbench/admin/knowledge')
    expect(cards[2].props('to')).toBe('/workbench/admin/auditList')
    expect(cards[3].props('to')).toBeUndefined()
  })
})
