import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const { mockElMessage, mockGetAlertMetrics } = vi.hoisted(() => ({
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockGetAlertMetrics: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
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
    Refresh: s('Refresh'),
    DataLine: s('DataLine'),
    WarningFilled: s('WarningFilled'),
    TrendCharts: s('TrendCharts'),
    Timer: s('Timer'),
  }
})

vi.mock('echarts', () => {
  const init = vi.fn(() => ({ setOption: vi.fn(), dispose: vi.fn() }))
  return {
    init,
    graphic: { LinearGradient: vi.fn() },
  }
})

vi.mock('@/api/system', () => ({
  getAlertMetrics: mockGetAlertMetrics,
}))

import Monitor from '@/pages/system/monitor.vue'

const metricsData = {
  rag_query: { total: 100, failures: 5, p95_latency: 2000, avg_latency: 1500 },
  milvus_search: { total: 80, failures: 2, p95_latency: 500, avg_latency: 400 },
  llm_call: { total: 50, failures: 15, p95_latency: 4000, avg_latency: 3000 },
}

describe('Monitor', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetAlertMetrics.mockResolvedValue(metricsData)
  })

  const tableColStub = {
    name: 'ElTableColumn',
    props: ['type', 'width', 'prop', 'label', 'fixed', 'align', 'minWidth', 'showOverflowTooltip'],
    template: '<div class="el-table-col-stub"></div>',
  }
  const mountMonitor = () =>
    mount(Monitor, {
      global: { stubs: { ...commonStubs, ...iconStubs, ElTableColumn: tableColStub } },
    })

  it('渲染性能监控看板标题', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    expect(wrapper.text()).toContain('性能监控看板')
  })

  it('渲染刷新按钮', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    expect(wrapper.text()).toContain('刷新')
  })

  it('渲染4个KPI标签', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('总调用量 (近10分钟)')
    expect(text).toContain('总失败数')
    expect(text).toContain('高失败率组件 (>10%)')
    expect(text).toContain('高延迟组件 (P95>3s)')
  })

  it('渲染图表区标题', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('各组件失败率 (%)')
    expect(text).toContain('各组件 P95 延迟 (ms)')
    expect(text).toContain('调用量分布')
    expect(text).toContain('指标明细')
  })

  it('渲染指标明细表格', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    expect(wrapper.find('.el-table-stub').exists()).toBe(true)
  })

  it('初始挂载调用getAlertMetrics', async () => {
    mountMonitor()
    await flushPromises()
    expect(mockGetAlertMetrics).toHaveBeenCalled()
  })

  it('KPI数字正确反映监控数据', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    const nums = wrapper.findAll('.kpi-num')
    expect(nums[0].text()).toBe('230')
    expect(nums[1].text()).toBe('22')
    expect(nums[2].text()).toBe('1')
    expect(nums[3].text()).toBe('1')
  })

  it('点击刷新调用getAlertMetrics', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    mockGetAlertMetrics.mockClear()
    const refreshBtn = wrapper.findAll('button').find((b) => b.text().includes('刷新'))
    await refreshBtn!.trigger('click')
    await flushPromises()
    expect(mockGetAlertMetrics).toHaveBeenCalled()
    vi.clearAllTimers()
  })

  it('刷新后KPI数字随新数据更新', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    mockGetAlertMetrics.mockResolvedValue({
      rag_query: { total: 200, failures: 10, p95_latency: 1000, avg_latency: 800 },
    })
    const refreshBtn = wrapper.findAll('button').find((b) => b.text().includes('刷新'))
    await refreshBtn!.trigger('click')
    await flushPromises()
    expect(mockGetAlertMetrics).toHaveBeenCalled()
    const nums = wrapper.findAll('.kpi-num')
    expect(nums[0].text()).toBe('200')
    expect(nums[1].text()).toBe('10')
    vi.clearAllTimers()
  })

  it('加载监控数据失败提示错误', async () => {
    mockGetAlertMetrics.mockRejectedValue(new Error('fail'))
    const wrapper = mountMonitor()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载监控数据失败')
    vi.clearAllTimers()
  })

  it('切换刷新间隔到关闭不抛错', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    wrapper.findComponent({ name: 'ElRadioGroup' }).vm.$emit('change', 0)
    await flushPromises()
    vi.clearAllTimers()
  })

  it('切换刷新间隔到30s不抛错', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    wrapper.findComponent({ name: 'ElRadioGroup' }).vm.$emit('change', 30)
    await flushPromises()
    vi.clearAllTimers()
  })

  it('覆盖v-model事件处理并卸载组件', async () => {
    const wrapper = mountMonitor()
    await flushPromises()
    const radio = wrapper.findComponent({ name: 'ElRadioGroup' })
    radio.vm.$emit('update:modelValue', 0)
    radio.vm.$emit('update:modelValue', 5)
    await flushPromises()
    vi.clearAllTimers()
    wrapper.unmount()
  })
})
