import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockRouterPush,
  mockElMessage,
  mockElMessageBox,
  mockElNotification,
  mockGetQAList,
  mockUpdateQAStatus,
} = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(() => Promise.resolve()),
  },
  mockElNotification: vi.fn(),
  mockGetQAList: vi.fn(),
  mockUpdateQAStatus: vi.fn(),
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
  Clock: defineComponent({ name: 'Clock', render: () => h('span', 'Clock') }),
  Select: defineComponent({ name: 'Select', render: () => h('span', 'Select') }),
  Files: defineComponent({ name: 'Files', render: () => h('span', 'Files') }),
}))

vi.mock('@/api/knowledge', () => ({
  getQAList: mockGetQAList,
  updateQAStatus: mockUpdateQAStatus,
}))

import Pending from '@/pages/audit/pending.vue'

const stubs = {
  ...commonStubs,
  ...iconStubs,
  Clock: defineComponent({ name: 'Clock', render: () => h('span', 'Clock') }),
  Select: defineComponent({ name: 'Select', render: () => h('span', 'Select') }),
  Files: defineComponent({ name: 'Files', render: () => h('span', 'Files') }),
  ElTableColumn: {
    name: 'ElTableColumn',
    props: ['type', 'width', 'prop', 'label', 'fixed', 'minWidth'],
    template:
      "<div class=\"el-table-col-stub\">{{ label }}<slot :row=\"{ id: 1, question: 'q', category_l1: '售后', category_l2: '', created_at: '2024-01-01' }\" /></div>",
  },
}

describe('pending', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    setActivePinia(createPinia())
    mockGetQAList.mockResolvedValue({ items: [], total: 0, page: 1, page_size: 10 })
    mockUpdateQAStatus.mockResolvedValue({})
  })

  it('renders 待审核新问题列表 title', () => {
    const wrapper = mount(Pending, { global: { stubs } })
    expect(wrapper.text()).toContain('待审核新问题列表')
  })

  it('renders 批量入库 button', () => {
    const wrapper = mount(Pending, { global: { stubs } })
    expect(wrapper.text()).toContain('批量入库')
  })

  it('renders 批量驳回 button', () => {
    const wrapper = mount(Pending, { global: { stubs } })
    expect(wrapper.text()).toContain('批量驳回')
  })

  it('renders KPI labels', () => {
    const wrapper = mount(Pending, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('待审核总数')
    expect(text).toContain('当前页条数')
    expect(text).toContain('已选中')
    expect(text).toContain('涉及分类')
  })

  it('renders table column labels', () => {
    const wrapper = mount(Pending, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('知识ID')
    expect(text).toContain('用户问题')
    expect(text).toContain('分类')
    expect(text).toContain('提交时间')
    expect(text).toContain('操作')
  })

  it('renders category filter select', () => {
    const wrapper = mount(Pending, { global: { stubs } })
    expect(wrapper.find('.el-select-stub').exists()).toBe(true)
  })

  it('calls getQAList on mount', () => {
    mount(Pending, { global: { stubs } })
    expect(mockGetQAList).toHaveBeenCalledWith({
      page: 1,
      page_size: 10,
      status: 'deprecated',
      category_l1: undefined,
    })
  })

  it('shows error message on load failure', async () => {
    mockGetQAList.mockRejectedValueOnce(new Error('fail'))
    mount(Pending, { global: { stubs } })
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载待审核列表失败')
  })

  it('点击行内入库按钮调用 updateQAStatus 并提示成功', async () => {
    const wrapper = mount(Pending, { global: { stubs } })
    await flushPromises()
    mockUpdateQAStatus.mockClear()
    const approveBtn = wrapper.findAll('button').find((b) => b.text() === '入库')
    await approveBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateQAStatus).toHaveBeenCalledWith(1, 'active')
    expect(mockElMessage.success).toHaveBeenCalledWith('已入库')
  })

  it('点击行内驳回按钮调用 updateQAStatus 归档', async () => {
    const wrapper = mount(Pending, { global: { stubs } })
    await flushPromises()
    mockUpdateQAStatus.mockClear()
    const rejectBtn = wrapper.findAll('button').find((b) => b.text() === '驳回')
    await rejectBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateQAStatus).toHaveBeenCalledWith(1, 'archived')
    expect(mockElMessage.success).toHaveBeenCalledWith('已驳回')
  })

  it('点击查看详情跳转 PendingDetail', async () => {
    const wrapper = mount(Pending, { global: { stubs } })
    await flushPromises()
    const detailBtn = wrapper.findAll('button').find((b) => b.text() === '查看详情')
    await detailBtn!.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith({ name: 'PendingDetail', query: { id: 1 } })
  })

  it('未勾选时批量入库提示警告', async () => {
    const wrapper = mount(Pending, { global: { stubs } })
    await flushPromises()
    const batchBtn = wrapper.findAll('button').find((b) => b.text() === '批量入库')
    await batchBtn!.trigger('click')
    expect(mockElMessage.warning).toHaveBeenCalledWith('请先勾选要入库的问题')
  })

  it('未勾选时批量驳回提示警告', async () => {
    const wrapper = mount(Pending, { global: { stubs } })
    await flushPromises()
    const batchBtn = wrapper.findAll('button').find((b) => b.text() === '批量驳回')
    await batchBtn!.trigger('click')
    expect(mockElMessage.warning).toHaveBeenCalledWith('请先勾选要驳回的问题')
  })

  it('切换分类筛选后带 category_l1 重新加载', async () => {
    const wrapper = mount(Pending, { global: { stubs } })
    await flushPromises()
    mockGetQAList.mockClear()
    const select = wrapper.findComponent({ name: 'ElSelect' })
    await select.vm.$emit('update:modelValue', '售后')
    await select.vm.$emit('change')
    await flushPromises()
    expect(mockGetQAList).toHaveBeenCalledWith({
      page: 1,
      page_size: 10,
      status: 'deprecated',
      category_l1: '售后',
    })
  })
})
