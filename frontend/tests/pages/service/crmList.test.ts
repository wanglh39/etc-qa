import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h, provide, inject } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const { mockRouterPush, mockElMessage, mockGetWorkOrders } = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockGetWorkOrders: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
  useRoute: () => ({ query: {} }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()), alert: vi.fn(() => Promise.resolve()) },
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => ({ ...iconStubs }))

vi.mock('@/api/audit', () => ({
  getWorkOrders: mockGetWorkOrders,
}))

import CrmList from '@/pages/service/crmList.vue'

const tableColStub = {
  name: 'ElTableColumn',
  props: ['type', 'width', 'prop', 'label', 'fixed', 'align', 'minWidth', 'showOverflowTooltip'],
  template: '<div class="el-table-col-stub">{{ label }}</div>',
}
const stubs = { ...commonStubs, ...iconStubs, ElTableColumn: tableColStub }

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
    props: ['type', 'width', 'prop', 'label', 'fixed', 'align', 'minWidth', 'showOverflowTooltip'],
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
      raw_data: JSON.stringify({ detail_desc: '问题1' }),
      created_at: '2024-01-01 10:00:00',
    },
    {
      id: 2,
      external_id: 'W002',
      status: 'processed',
      raw_data: JSON.stringify({ detail_desc: '问题2' }),
      created_at: '2024-01-02 11:00:00',
    },
  ],
  total: 2,
}

describe('crmList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetWorkOrders.mockResolvedValue(tableItems)
  })

  it('渲染页面标题 CRM工单列表', () => {
    const wrapper = mount(CrmList, { global: { stubs } })
    expect(wrapper.text()).toContain('CRM工单列表')
  })

  it('渲染新建工单按钮', () => {
    const wrapper = mount(CrmList, { global: { stubs } })
    expect(wrapper.text()).toContain('新建工单')
  })

  it('渲染搜索区 查询 重置 按钮', () => {
    const wrapper = mount(CrmList, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('查询')
    expect(text).toContain('重置')
  })

  it('渲染表格列头', () => {
    const wrapper = mount(CrmList, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('工单ID')
    expect(text).toContain('外部ID')
    expect(text).toContain('工单内容')
    expect(text).toContain('状态')
    expect(text).toContain('创建时间')
  })

  it('渲染表格与分页组件', () => {
    const wrapper = mount(CrmList, { global: { stubs } })
    expect(wrapper.find('.el-table-stub').exists()).toBe(true)
    expect(wrapper.find('.el-pagination-stub').exists()).toBe(true)
  })

  it('挂载时调用 getWorkOrders', async () => {
    mount(CrmList, { global: { stubs } })
    await flushPromises()
    expect(mockGetWorkOrders).toHaveBeenCalled()
  })

  it('加载失败时提示错误', async () => {
    mockGetWorkOrders.mockRejectedValueOnce(new Error('fail'))
    mount(CrmList, { global: { stubs } })
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载工单列表失败')
  })

  it('点击重置按钮提示已重置', async () => {
    const wrapper = mount(CrmList, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const resetBtn = buttons.find((b) => b.text() === '重置')
    await resetBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.info).toHaveBeenCalledWith('搜索条件已重置')
  })

  it('点击查询按钮调用 getWorkOrders 带默认参数', async () => {
    const wrapper = mount(CrmList, { global: { stubs } })
    await flushPromises()
    mockGetWorkOrders.mockClear()
    const queryBtn = wrapper.findAll('button').find((b) => b.text() === '查询')!
    await queryBtn.trigger('click')
    await flushPromises()
    expect(mockGetWorkOrders).toHaveBeenCalledWith({ page: 1, page_size: 10, status: undefined })
  })

  it('选择状态后查询带 status 参数', async () => {
    const wrapper = mount(CrmList, { global: { stubs } })
    await flushPromises()
    const select = wrapper.findComponent({ name: 'ElSelect' })
    await select.vm.$emit('update:modelValue', 'submitted')
    await flushPromises()
    mockGetWorkOrders.mockClear()
    const queryBtn = wrapper.findAll('button').find((b) => b.text() === '查询')!
    await queryBtn.trigger('click')
    await flushPromises()
    expect(mockGetWorkOrders).toHaveBeenCalledWith({ page: 1, page_size: 10, status: 'submitted' })
  })

  it('分页 change 事件触发 getWorkOrders 带新页码', async () => {
    const wrapper = mount(CrmList, { global: { stubs } })
    await flushPromises()
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    await pagination.vm.$emit('update:current-page', 2)
    await pagination.vm.$emit('change')
    await flushPromises()
    expect(mockGetWorkOrders).toHaveBeenLastCalledWith({
      page: 2,
      page_size: 10,
      status: undefined,
    })
  })

  it('点击新建工单跳转到创建页', async () => {
    const wrapper = mount(CrmList, {
      global: { stubs, config: { globalProperties: { $router: { push: mockRouterPush } } } },
    })
    await flushPromises()
    const newBtn = wrapper.findAll('button').find((b) => b.text() === '新建工单')!
    await newBtn.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/crm/create')
  })

  it('表格渲染行数据触发状态映射与内容解析', async () => {
    const wrapper = mount(CrmList, { global: { stubs: rowStubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('已提交')
    expect(text).toContain('已处理')
    expect(text).toContain('问题1')
    expect(text).toContain('问题2')
  })
})
