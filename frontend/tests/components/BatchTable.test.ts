import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'

const { mockElMessage, mockClearSelection } = vi.hoisted(() => ({
  mockElMessage: {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
  mockClearSelection: vi.fn(),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
}))

import BatchTable from '@/components/BatchTable.vue'

const stubs = {
  ElTable: {
    name: 'ElTable',
    props: ['data', 'border', 'stripe', 'rowKey'],
    emits: ['selection-change'],
    setup(_, { expose }) {
      expose({ clearSelection: mockClearSelection })
    },
    template: '<div class="el-table-stub"><slot></slot></div>',
  },
  ElTableColumn: {
    name: 'ElTableColumn',
    props: ['type', 'width'],
    template: '<div><slot></slot></div>',
  },
  ElPagination: {
    name: 'ElPagination',
    props: ['total', 'pageSize', 'currentPage', 'background', 'layout'],
    emits: ['size-change', 'current-change'],
    template: '<div class="el-pagination-stub"></div>',
  },
  ElButton: {
    name: 'ElButton',
    props: ['type'],
    emits: ['click'],
    template: '<button @click="$emit(\'click\')"><slot></slot></button>',
  },
  ElSpace: { name: 'ElSpace', template: '<div class="el-space-stub"><slot></slot></div>' },
}

describe('BatchTable', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const baseProps = {
    tableData: [
      { id: 1, name: 'a' },
      { id: 2, name: 'b' },
    ],
    total: 2,
    pageNum: 1,
    pageSize: 10,
  }

  it('renders batch bar when showBatch is true', () => {
    const wrapper = mount(BatchTable, {
      props: { ...baseProps, showBatch: true, batchText: '删除' },
      global: { stubs },
    })
    expect(wrapper.find('.batch-bar').exists()).toBe(true)
    expect(wrapper.text()).toContain('批量删除')
  })

  it('hides batch bar when showBatch is false', () => {
    const wrapper = mount(BatchTable, {
      props: { ...baseProps, showBatch: false },
      global: { stubs },
    })
    expect(wrapper.find('.batch-bar').exists()).toBe(false)
  })

  it('hides batch bar when showBatch is undefined', () => {
    const wrapper = mount(BatchTable, {
      props: baseProps,
      global: { stubs },
    })
    expect(wrapper.find('.batch-bar').exists()).toBe(false)
  })

  it('shows default batchText as empty when not provided', () => {
    const wrapper = mount(BatchTable, {
      props: { ...baseProps, showBatch: true },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('批量')
  })

  it('shows selection count when items are selected', async () => {
    const wrapper = mount(BatchTable, {
      props: { ...baseProps, showBatch: true, batchText: '操作' },
      global: { stubs },
    })
    const elTable = wrapper.findComponent({ name: 'ElTable' })
    elTable.vm.$emit('selection-change', [{ id: 1 }, { id: 3 }])
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('已选中2条数据')
  })

  it('does not show count when no items selected', () => {
    const wrapper = mount(BatchTable, {
      props: { ...baseProps, showBatch: true, batchText: '操作' },
      global: { stubs },
    })
    expect(wrapper.text()).not.toContain('已选中')
  })

  it('emits batch with selected items when batchHandle called with selection', async () => {
    const wrapper = mount(BatchTable, {
      props: { ...baseProps, showBatch: true, batchText: '删除' },
      global: { stubs },
    })
    const elTable = wrapper.findComponent({ name: 'ElTable' })
    elTable.vm.$emit('selection-change', [{ id: 1 }, { id: 2 }])
    await wrapper.vm.$nextTick()

    const buttons = wrapper.findAll('button')
    const batchBtn = buttons.find((b) => b.text().includes('批量删除'))
    await batchBtn!.trigger('click')

    expect(wrapper.emitted('batch')).toBeTruthy()
    expect(wrapper.emitted('batch')![0]).toEqual([[{ id: 1 }, { id: 2 }]])
  })

  it('shows warning and does not emit batch when no selection', async () => {
    const wrapper = mount(BatchTable, {
      props: { ...baseProps, showBatch: true, batchText: '删除' },
      global: { stubs },
    })
    const buttons = wrapper.findAll('button')
    const batchBtn = buttons.find((b) => b.text().includes('批量删除'))
    await batchBtn!.trigger('click')

    expect(mockElMessage.warning).toHaveBeenCalledWith('请先勾选需要操作的数据')
    expect(wrapper.emitted('batch')).toBeFalsy()
  })

  it('renders table with correct data prop', () => {
    const wrapper = mount(BatchTable, {
      props: baseProps,
      global: { stubs },
    })
    const elTable = wrapper.findComponent({ name: 'ElTable' })
    expect(elTable.props('data')).toEqual(baseProps.tableData)
  })

  it('renders pagination with correct total and page props', () => {
    const wrapper = mount(BatchTable, {
      props: { ...baseProps, total: 100, pageNum: 5, pageSize: 20 },
      global: { stubs },
    })
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    expect(pagination.props('total')).toBe(100)
    expect(pagination.props('pageSize')).toBe(20)
    expect(pagination.props('currentPage')).toBe(5)
  })

  it('emits update:pageNum and page-change on current-change', async () => {
    const wrapper = mount(BatchTable, {
      props: baseProps,
      global: { stubs },
    })
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    pagination.vm.$emit('current-change', 3)
    expect(wrapper.emitted('update:pageNum')).toBeTruthy()
    expect(wrapper.emitted('update:pageNum')![0]).toEqual([3])
    expect(wrapper.emitted('page-change')).toBeTruthy()
  })

  it('emits update:pageSize and page-change on size-change', async () => {
    const wrapper = mount(BatchTable, {
      props: baseProps,
      global: { stubs },
    })
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    pagination.vm.$emit('size-change', 50)
    expect(wrapper.emitted('update:pageSize')).toBeTruthy()
    expect(wrapper.emitted('update:pageSize')![0]).toEqual([50])
    expect(wrapper.emitted('page-change')).toBeTruthy()
  })

  it('clearSelection calls table clearSelection and empties selectedList', async () => {
    const wrapper = mount(BatchTable, {
      props: { ...baseProps, showBatch: true, batchText: '删除' },
      global: { stubs },
    })
    const elTable = wrapper.findComponent({ name: 'ElTable' })
    elTable.vm.$emit('selection-change', [{ id: 1 }, { id: 2 }])
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('已选中2条数据')

    const buttons = wrapper.findAll('button')
    const clearBtn = buttons.find((b) => b.text() === '清空选中')
    await clearBtn!.trigger('click')

    expect(mockClearSelection).toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('已选中')
  })
})
