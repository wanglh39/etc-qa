import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const { mockElMessage, mockGetAlertList, mockAckAlert } = vi.hoisted(() => ({
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockGetAlertList: vi.fn(),
  mockAckAlert: vi.fn(),
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
    BellFilled: s('BellFilled'),
    WarningFilled: s('WarningFilled'),
    InfoFilled: s('InfoFilled'),
    CircleCheck: s('CircleCheck'),
    Warning: s('Warning'),
    Refresh: s('Refresh'),
  }
})

vi.mock('@/api/system', () => ({
  getAlertList: mockGetAlertList,
  ackAlert: mockAckAlert,
}))

import Alert from '@/pages/system/alert.vue'

const alertList = {
  items: [
    {
      id: 1,
      rule_id: 'rule_p0',
      severity: 'P0',
      message: 'CPU过高',
      current_value: 95.5,
      threshold_value: 90,
      status: 'open',
      acked_by: null,
      acked_at: null,
      created_at: '2024-01-01 00:00:00',
    },
    {
      id: 2,
      rule_id: 'rule_p1',
      severity: 'P1',
      message: '内存告警',
      current_value: 85,
      threshold_value: 80,
      status: 'open',
      acked_by: null,
      acked_at: null,
      created_at: '2024-01-02 00:00:00',
    },
    {
      id: 3,
      rule_id: 'rule_p2',
      severity: 'P2',
      message: '磁盘提醒',
      current_value: 70,
      threshold_value: 75,
      status: 'acked',
      acked_by: 'ops',
      acked_at: '2024-01-03 00:00:00',
      created_at: '2024-01-03 00:00:00',
    },
  ],
  total: 3,
  page: 1,
  page_size: 20,
}

describe('Alert', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetAlertList.mockResolvedValue(alertList)
  })

  const mockRow = {
    id: 1,
    rule_id: 'rule_p0',
    severity: 'P0',
    message: 'CPU过高',
    current_value: 95.5,
    threshold_value: 90,
    status: 'open',
    acked_by: null,
    acked_at: null,
    created_at: '2024-01-01 00:00:00',
  }
  const tableColStub = {
    name: 'ElTableColumn',
    props: [
      'type',
      'width',
      'prop',
      'label',
      'fixed',
      'align',
      'minWidth',
      'showOverflowTooltip',
      'selectable',
    ],
    data: () => ({ row: mockRow }),
    template: '<div class="el-table-col-stub"><slot :row="row" /></div>',
  }
  const mountAlert = () =>
    mount(Alert, {
      global: { stubs: { ...commonStubs, ...iconStubs, ElTableColumn: tableColStub } },
    })

  it('渲染异常告警标题', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    expect(wrapper.text()).toContain('异常告警')
  })

  it('渲染4个级别KPI标签', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('P0 紧急')
    expect(text).toContain('P1 严重')
    expect(text).toContain('P2 提醒')
    expect(text).toContain('未确认')
  })

  it('渲染刷新按钮', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    expect(wrapper.text()).toContain('刷新')
  })

  it('渲染筛选区与搜索重置按钮', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    expect(wrapper.findAll('.el-select-stub').length).toBeGreaterThanOrEqual(2)
    const text = wrapper.text()
    expect(text).toContain('搜索')
    expect(text).toContain('重置')
  })

  it('渲染表格与分页组件', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    expect(wrapper.find('.el-table-stub').exists()).toBe(true)
    expect(wrapper.find('.el-pagination-stub').exists()).toBe(true)
  })

  it('初始挂载调用getAlertList', async () => {
    mountAlert()
    await flushPromises()
    expect(mockGetAlertList).toHaveBeenCalled()
  })

  it('KPI数字正确反映告警数据', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    const nums = wrapper.findAll('.kpi-num')
    expect(nums[0].text()).toBe('1')
    expect(nums[1].text()).toBe('1')
    expect(nums[2].text()).toBe('1')
    expect(nums[3].text()).toBe('2')
  })

  it('点击确认按钮调用ackAlert并提示成功', async () => {
    mockAckAlert.mockResolvedValue({})
    const wrapper = mountAlert()
    await flushPromises()
    const ackBtn = wrapper.findAll('button').find((b) => b.text().includes('确认'))
    expect(ackBtn).toBeDefined()
    await ackBtn!.trigger('click')
    await flushPromises()
    expect(mockAckAlert).toHaveBeenCalledWith(1)
    expect(mockElMessage.success).toHaveBeenCalledWith('告警已确认')
    vi.clearAllTimers()
  })

  it('确认告警失败提示错误', async () => {
    mockAckAlert.mockRejectedValue(new Error('fail'))
    const wrapper = mountAlert()
    await flushPromises()
    const ackBtn = wrapper.findAll('button').find((b) => b.text().includes('确认'))
    await ackBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('确认失败')
    vi.clearAllTimers()
  })

  it('点击搜索调用getAlertList重新加载', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    mockGetAlertList.mockClear()
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索')
    await searchBtn!.trigger('click')
    await flushPromises()
    expect(mockGetAlertList).toHaveBeenCalled()
    vi.clearAllTimers()
  })

  it('点击重置清空筛选并重新加载', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    mockGetAlertList.mockClear()
    const resetBtn = wrapper.findAll('button').find((b) => b.text() === '重置')
    await resetBtn!.trigger('click')
    await flushPromises()
    expect(mockGetAlertList).toHaveBeenCalled()
    vi.clearAllTimers()
  })

  it('批量确认调用ackAlert并提示成功', async () => {
    mockAckAlert.mockResolvedValue({})
    const wrapper = mountAlert()
    await flushPromises()
    wrapper.findComponent({ name: 'ElTable' }).vm.$emit('selection-change', [
      {
        id: 1,
        rule_id: 'rule_p0',
        severity: 'P0',
        message: 'CPU过高',
        current_value: 95.5,
        threshold_value: 90,
        status: 'open',
        acked_by: null,
        acked_at: null,
        created_at: '2024-01-01 00:00:00',
      },
      {
        id: 2,
        rule_id: 'rule_p1',
        severity: 'P1',
        message: '内存告警',
        current_value: 85,
        threshold_value: 80,
        status: 'open',
        acked_by: null,
        acked_at: null,
        created_at: '2024-01-02 00:00:00',
      },
    ])
    await flushPromises()
    const batchBtn = wrapper.findAll('button').find((b) => b.text().includes('批量确认'))
    expect(batchBtn).toBeDefined()
    await batchBtn!.trigger('click')
    await flushPromises()
    expect(mockAckAlert).toHaveBeenCalledTimes(2)
    expect(mockElMessage.success).toHaveBeenCalled()
    vi.clearAllTimers()
  })

  it('分页current-change触发重新加载', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    mockGetAlertList.mockClear()
    wrapper.findComponent({ name: 'ElPagination' }).vm.$emit('current-change', 2)
    await flushPromises()
    expect(mockGetAlertList).toHaveBeenCalled()
    vi.clearAllTimers()
  })

  it('加载告警列表失败提示错误', async () => {
    mockGetAlertList.mockRejectedValue(new Error('fail'))
    const wrapper = mountAlert()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载告警列表失败')
    vi.clearAllTimers()
  })

  it('分页size-change触发重新加载', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    mockGetAlertList.mockClear()
    wrapper.findComponent({ name: 'ElPagination' }).vm.$emit('size-change', 50)
    await flushPromises()
    expect(mockGetAlertList).toHaveBeenCalled()
    vi.clearAllTimers()
  })

  it('覆盖所有v-model事件处理并卸载组件', async () => {
    const wrapper = mountAlert()
    await flushPromises()
    const selects = wrapper.findAllComponents({ name: 'ElSelect' })
    selects.forEach((s) => s.vm.$emit('update:modelValue', 'x'))
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    pagination.vm.$emit('update:currentPage', 2)
    pagination.vm.$emit('update:pageSize', 20)
    await flushPromises()
    vi.clearAllTimers()
    wrapper.unmount()
  })
})
