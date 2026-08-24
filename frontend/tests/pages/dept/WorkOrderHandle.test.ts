import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h, provide, inject } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockRouterPush,
  mockElMessage,
  mockElMessageBox,
  mockGetWorkOrders,
  mockGetWorkOrderStats,
  mockReplyWorkOrder,
} = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(() => Promise.resolve()),
  },
  mockGetWorkOrders: vi.fn(),
  mockGetWorkOrderStats: vi.fn(),
  mockReplyWorkOrder: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
  useRoute: () => ({ params: { deptCode: 'aftersale' } }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: mockElMessageBox,
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => ({
  ...iconStubs,
  Clock: defineComponent({ name: 'Clock', render: () => h('span') }),
  Calendar: defineComponent({ name: 'Calendar', render: () => h('span') }),
}))

vi.mock('@/api/audit', () => ({
  getWorkOrders: mockGetWorkOrders,
  getWorkOrderStats: mockGetWorkOrderStats,
}))

vi.mock('@/api/workorder', () => ({
  replyWorkOrder: mockReplyWorkOrder,
}))

import WorkOrderHandle from '@/pages/dept/WorkOrderHandle.vue'

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
  template: '<div class="el-table-col-stub">{{ label }}</div>',
}
const stubs = { ...commonStubs, ...iconStubs, ElTableColumn: tableColStub }
const directives = { loading: { mounted: () => {}, updated: () => {} } }

const rowStubs = {
  ...commonStubs,
  ...iconStubs,
  ElTable: defineComponent({
    name: 'ElTable',
    props: ['data', 'border', 'stripe', 'rowKey'],
    emits: ['selection-change'],
    setup(props, { slots }) {
      provide('elTableProps', props)
      return () => h('div', { class: 'el-table-stub' }, slots.default?.())
    },
  }),
  ElTableColumn: defineComponent({
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
    setup(props, { slots }) {
      const tableProps = inject<any>('elTableProps', { data: [] })
      return () =>
        h('div', { class: 'el-table-col-stub' }, [
          props.label,
          tableProps.data.map((row) => slots.default?.({ row })),
        ])
    },
  }),
}

const tableItems = {
  items: [
    {
      id: 1,
      external_id: 'W001',
      status: 'submitted',
      raw_data: JSON.stringify({ problem_type: '产品咨询', priority: '高' }),
      created_at: '2024-01-01 10:00:00',
    },
    {
      id: 2,
      external_id: 'W002',
      status: 'processed',
      raw_data: JSON.stringify({ problem_type: '售后退换', priority: '中' }),
      created_at: '2024-01-02 11:00:00',
    },
  ],
  total: 2,
}
const statsData = { total: 10, submitted: 3, answered: 2, processed: 5, today: 1 }

describe('workOrderHandle', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetWorkOrders.mockResolvedValue(tableItems)
    mockGetWorkOrderStats.mockResolvedValue(statsData)
    mockReplyWorkOrder.mockResolvedValue({})
  })

  const mountHandle = () => mount(WorkOrderHandle, { global: { stubs, directives } })

  it('渲染KPI概览标签', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('全部工单')
    expect(text).toContain('待处理')
    expect(text).toContain('已回复')
    expect(text).toContain('已办结')
    expect(text).toContain('今日新增')
  })

  it('渲染部门工单处理标题', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    expect(wrapper.text()).toContain('售后处理部工单处理')
  })

  it('渲染Tab状态筛选 全部 待处理 已回复 已办结', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('全部')
    expect(text).toContain('已回复')
  })

  it('渲染搜索区 查询 重置 按钮', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('查询')
    expect(text).toContain('重置')
  })

  it('渲染表格列头', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('工单ID')
    expect(text).toContain('工单编号')
    expect(text).toContain('问题类型')
    expect(text).toContain('优先级')
    expect(text).toContain('提交时间')
    expect(text).toContain('工单状态')
    expect(text).toContain('操作')
  })

  it('渲染表格与分页组件', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    expect(wrapper.find('.el-table-stub').exists()).toBe(true)
    expect(wrapper.find('.el-pagination-stub').exists()).toBe(true)
  })

  it('挂载时调用 getWorkOrders 与 getWorkOrderStats', async () => {
    mountHandle()
    await flushPromises()
    expect(mockGetWorkOrders).toHaveBeenCalled()
    expect(mockGetWorkOrderStats).toHaveBeenCalled()
  })

  it('加载列表失败时提示错误', async () => {
    mockGetWorkOrders.mockRejectedValueOnce(new Error('fail'))
    mountHandle()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载工单列表失败')
  })

  it('点击查询按钮调用 getWorkOrders 带 dept 参数', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    mockGetWorkOrders.mockClear()
    const queryBtn = wrapper.findAll('button').find((b) => b.text() === '查询')!
    await queryBtn.trigger('click')
    await flushPromises()
    expect(mockGetWorkOrders).toHaveBeenCalledWith({
      page: 1,
      page_size: 10,
      dept: 'aftersale',
      status: undefined,
    })
  })

  it('点击重置按钮重新加载列表', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    mockGetWorkOrders.mockClear()
    const resetBtn = wrapper.findAll('button').find((b) => b.text() === '重置')!
    await resetBtn.trigger('click')
    await flushPromises()
    expect(mockGetWorkOrders).toHaveBeenCalledWith({
      page: 1,
      page_size: 10,
      dept: 'aftersale',
      status: undefined,
    })
  })

  it('点击待处理KPI卡片按 submitted 筛选', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    mockGetWorkOrders.mockClear()
    const kpiCards = wrapper.findAll('.el-card-stub')
    await kpiCards[1].trigger('click')
    await flushPromises()
    expect(mockGetWorkOrders).toHaveBeenCalledWith({
      page: 1,
      page_size: 10,
      dept: 'aftersale',
      status: 'submitted',
    })
  })

  it('切换Tab触发 getWorkOrders 带新状态', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    mockGetWorkOrders.mockClear()
    const tabs = wrapper.findComponent({ name: 'ElTabs' })
    await tabs.vm.$emit('update:modelValue', 'answered')
    await tabs.vm.$emit('tab-change')
    await flushPromises()
    expect(mockGetWorkOrders).toHaveBeenCalledWith({
      page: 1,
      page_size: 10,
      dept: 'aftersale',
      status: 'answered',
    })
  })

  it('分页 current-change 触发 getWorkOrders 带新页码', async () => {
    const wrapper = mountHandle()
    await flushPromises()
    mockGetWorkOrders.mockClear()
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    await pagination.vm.$emit('update:current-page', 2)
    await pagination.vm.$emit('current-change', 2)
    await flushPromises()
    expect(mockGetWorkOrders).toHaveBeenLastCalledWith({
      page: 2,
      page_size: 10,
      dept: 'aftersale',
      status: undefined,
    })
  })

  it('点击办结按钮确认后调用 replyWorkOrder 办结', async () => {
    const wrapper = mount(WorkOrderHandle, { global: { stubs: rowStubs, directives } })
    await flushPromises()
    mockReplyWorkOrder.mockClear()
    const finishBtn = wrapper.findAll('button').find((b) => b.text() === '办结')!
    await finishBtn.trigger('click')
    await flushPromises()
    expect(mockElMessageBox.confirm).toHaveBeenCalled()
    expect(mockReplyWorkOrder).toHaveBeenCalledWith(1, { handle_remark: '快速办结' })
    expect(mockElMessage.success).toHaveBeenCalledWith('工单W001已办结')
  })

  it('办结取消确认提示失败', async () => {
    mockElMessageBox.confirm.mockRejectedValueOnce(new Error('cancel'))
    const wrapper = mount(WorkOrderHandle, { global: { stubs: rowStubs, directives } })
    await flushPromises()
    const finishBtn = wrapper.findAll('button').find((b) => b.text() === '办结')!
    await finishBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('办结失败')
  })

  it('点击查看详情跳转详情页', async () => {
    const wrapper = mount(WorkOrderHandle, { global: { stubs: rowStubs, directives } })
    await flushPromises()
    const detailBtn = wrapper.findAll('button').find((b) => b.text() === '查看详情')!
    await detailBtn.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith({ path: '/dept/handle/aftersale/detail/1' })
  })

  it('选中工单后批量办结调用 replyWorkOrder', async () => {
    const wrapper = mount(WorkOrderHandle, { global: { stubs: rowStubs, directives } })
    await flushPromises()
    const table = wrapper.findComponent({ name: 'ElTable' })
    await table.vm.$emit('selection-change', tableItems.items)
    await flushPromises()
    mockReplyWorkOrder.mockClear()
    const batchBtn = wrapper.findAll('button').find((b) => b.text().includes('批量办结'))!
    await batchBtn.trigger('click')
    await flushPromises()
    expect(mockElMessageBox.confirm).toHaveBeenCalled()
    expect(mockReplyWorkOrder).toHaveBeenCalledTimes(2)
    expect(mockElMessage.success).toHaveBeenCalled()
  })
})
