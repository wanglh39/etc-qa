import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockRouterPush,
  mockRouterBack,
  mockRoute,
  mockElMessage,
  mockElMessageBox,
  mockElNotification,
  mockGetQADetail,
  mockUpdateQAStatus,
} = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockRouterBack: vi.fn(),
  mockRoute: { query: { id: '1' } },
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(() => Promise.resolve()),
  },
  mockElNotification: vi.fn(),
  mockGetQADetail: vi.fn(),
  mockUpdateQAStatus: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush, back: mockRouterBack }),
  useRoute: () => mockRoute,
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: mockElMessageBox,
  ElNotification: mockElNotification,
}))

vi.mock('@element-plus/icons-vue', () => ({
  ...iconStubs,
}))

vi.mock('@/api/knowledge', () => ({
  getQADetail: mockGetQADetail,
  updateQAStatus: mockUpdateQAStatus,
}))

import PendingDetail from '@/pages/audit/pendingDetail.vue'

const stubs = {
  ...commonStubs,
  ...iconStubs,
  ElDescriptionsItem: {
    name: 'ElDescriptionsItem',
    props: ['label', 'span'],
    template:
      '<div class="el-descriptions-item-stub"><span class="desc-label">{{ label }}</span><slot></slot></div>',
  },
  ElInput: {
    name: 'ElInput',
    props: ['modelValue', 'placeholder', 'type', 'clearable', 'disabled', 'size', 'rows'],
    emits: ['update:modelValue', 'change', 'blur', 'focus'],
    template:
      '<input :value="modelValue" :placeholder="placeholder" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  },
}

describe('pendingDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    setActivePinia(createPinia())
    mockRoute.query = { id: '1' }
    mockGetQADetail.mockResolvedValue({
      id: 1,
      question: '质保多久',
      answer: '一年',
      category_l1: '售后',
      category_l2: '质保',
      internal_process: '流程A',
      feedback_dept: '售后部',
      status: 'deprecated',
      created_at: '2024-01-01',
    })
    mockUpdateQAStatus.mockResolvedValue({})
  })

  it('renders 工单审核详情 title', () => {
    const wrapper = mount(PendingDetail, { global: { stubs } })
    expect(wrapper.text()).toContain('工单审核详情')
  })

  it('renders 确认入库 button', () => {
    const wrapper = mount(PendingDetail, { global: { stubs } })
    expect(wrapper.text()).toContain('确认入库')
  })

  it('renders 驳回工单 button', () => {
    const wrapper = mount(PendingDetail, { global: { stubs } })
    expect(wrapper.text()).toContain('驳回工单')
  })

  it('renders description labels', () => {
    const wrapper = mount(PendingDetail, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('知识ID')
    expect(text).toContain('分类')
    expect(text).toContain('提交时间')
    expect(text).toContain('状态')
    expect(text).toContain('用户问题')
    expect(text).toContain('标准答案')
  })

  it('renders remark input placeholder', () => {
    const wrapper = mount(PendingDetail, { global: { stubs } })
    const inputs = wrapper.findAll('input')
    const placeholders = inputs.map((i) => i.attributes('placeholder'))
    expect(placeholders.some((p) => p && p.includes('请填写入库或驳回的详细备注'))).toBe(true)
  })

  it('calls getQADetail on mount with route id', () => {
    mount(PendingDetail, { global: { stubs } })
    expect(mockGetQADetail).toHaveBeenCalledWith(1)
  })

  it('shows error when id is missing', async () => {
    mockRoute.query = {}
    mount(PendingDetail, { global: { stubs } })
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('缺少工单ID')
  })

  it('warns when auditing without remark', async () => {
    const wrapper = mount(PendingDetail, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const passBtn = buttons.find((b) => b.text().includes('确认入库'))
    await passBtn.trigger('click')
    expect(mockElMessage.warning).toHaveBeenCalledWith('请先填写处理备注')
  })

  it('填写备注后确认入库调用 updateQAStatus 并提示成功', async () => {
    const wrapper = mount(PendingDetail, { global: { stubs } })
    await flushPromises()
    const remarkInput = wrapper.findComponent({ name: 'ElInput' })
    await remarkInput.vm.$emit('update:modelValue', '同意入库，答案准确')
    await flushPromises()
    const passBtn = wrapper.findAll('button').find((b) => b.text().includes('确认入库'))
    await passBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateQAStatus).toHaveBeenCalledWith(1, 'active')
    expect(mockElMessage.success).toHaveBeenCalledWith('入库成功')
  })

  it('填写备注后驳回工单调用 updateQAStatus 归档', async () => {
    const wrapper = mount(PendingDetail, { global: { stubs } })
    await flushPromises()
    const remarkInput = wrapper.findComponent({ name: 'ElInput' })
    await remarkInput.vm.$emit('update:modelValue', '问题重复，予以驳回')
    await flushPromises()
    const rejectBtn = wrapper.findAll('button').find((b) => b.text().includes('驳回工单'))
    await rejectBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateQAStatus).toHaveBeenCalledWith(1, 'archived')
    expect(mockElMessage.success).toHaveBeenCalledWith('已驳回')
  })

  it('updateQAStatus 失败时提示操作失败', async () => {
    mockUpdateQAStatus.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(PendingDetail, { global: { stubs } })
    await flushPromises()
    const remarkInput = wrapper.findComponent({ name: 'ElInput' })
    await remarkInput.vm.$emit('update:modelValue', '备注内容')
    await flushPromises()
    const passBtn = wrapper.findAll('button').find((b) => b.text().includes('确认入库'))
    await passBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('操作失败')
  })

  it('缺少 id 时不调用 getQADetail', async () => {
    mockRoute.query = {}
    mount(PendingDetail, { global: { stubs } })
    await flushPromises()
    expect(mockGetQADetail).not.toHaveBeenCalled()
  })
})
