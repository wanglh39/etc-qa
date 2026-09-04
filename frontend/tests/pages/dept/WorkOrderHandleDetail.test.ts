import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockRouterBack,
  mockElMessage,
  mockGetWorkOrderDetail,
  mockReplyWorkOrder,
  mockQueryQA,
  mockGetDeptList,
} = vi.hoisted(() => ({
  mockRouterBack: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockGetWorkOrderDetail: vi.fn(),
  mockReplyWorkOrder: vi.fn(),
  mockQueryQA: vi.fn(),
  mockGetDeptList: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), back: mockRouterBack }),
  useRoute: () => ({ params: { deptCode: 'aftersale', orderId: '1' } }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()), alert: vi.fn(() => Promise.resolve()) },
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => ({
  ...iconStubs,
  CopyDocument: defineComponent({ name: 'CopyDocument', render: () => h('span') }),
  DocumentRemove: defineComponent({ name: 'DocumentRemove', render: () => h('span') }),
}))

vi.mock('@/api/workorder', () => ({
  getWorkOrderDetail: mockGetWorkOrderDetail,
  replyWorkOrder: mockReplyWorkOrder,
}))

vi.mock('@/api/workbench', () => ({
  queryQA: mockQueryQA,
}))

vi.mock('@/api/system', () => ({
  getDeptList: mockGetDeptList,
}))

import WorkOrderHandleDetail from '@/pages/dept/WorkOrderHandleDetail.vue'

const stubs = {
  ...commonStubs,
  ...iconStubs,
  ElDescriptionsItem: {
    name: 'ElDescriptionsItem',
    props: ['label', 'span'],
    template:
      '<div class="el-descriptions-item-stub"><span class="desc-label">{{ label }}</span><slot></slot></div>',
  },
}
const directives = { loading: { mounted: () => {}, updated: () => {} } }

const orderDetail = {
  id: 1,
  external_id: 'W001',
  status: 'submitted',
  dept: 'aftersale',
  service_id: 'S001',
  customer_name: '张三',
  phone: '13800138000',
  problem_type: '产品咨询',
  next_dept: 'aftersale',
  priority: '高',
  detail_desc: '客户咨询退款流程',
  handle_remark: '',
  created_at: '2024-01-01 10:00:00',
  updated_at: '',
}

describe('workOrderHandleDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetWorkOrderDetail.mockResolvedValue(orderDetail)
    mockReplyWorkOrder.mockResolvedValue({})
    mockQueryQA.mockResolvedValue({ candidates: [], confidence: 'none' })
    mockGetDeptList.mockResolvedValue([
      { dept_key: 'aftersale', dept_name: '售后处理部' },
      { dept_key: 'tech', dept_name: '技术运维部' },
      { dept_key: 'finance', dept_name: '财务部' },
      { dept_key: 'market', dept_name: '市场部' },
      { dept_key: 'hr', dept_name: '人事部' },
    ])
  })

  const mountDetail = () => mount(WorkOrderHandleDetail, { global: { stubs, directives } })

  it('渲染返回按钮与页面标题', async () => {
    const wrapper = mountDetail()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('返回')
    expect(text).toContain('工单列表')
    expect(text).toContain('工单详情')
  })

  it('渲染工单基础信息区', async () => {
    const wrapper = mountDetail()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('工单基础信息')
    expect(text).toContain('工单ID')
    expect(text).toContain('工单编号')
    expect(text).toContain('提交时间')
    expect(text).toContain('问题类型')
    expect(text).toContain('客户名称')
    expect(text).toContain('客户手机号')
    expect(text).toContain('问题描述')
  })

  it('渲染处理时间线与处理备注区', async () => {
    const wrapper = mountDetail()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('处理时间线')
    expect(text).toContain('处理备注')
  })

  it('渲染快捷模板与办结按钮', async () => {
    const wrapper = mountDetail()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('快捷模板')
    expect(text).toContain('已解决')
    expect(text).toContain('需转交')
    expect(text).toContain('待补充材料')
    expect(text).toContain('已退款')
    expect(text).toContain('办结工单')
  })

  it('渲染知识库检索区', async () => {
    const wrapper = mountDetail()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('知识库检索')
    expect(text).toContain('重新搜索')
    expect(text).toContain('搜索')
    expect(text).toContain('暂无匹配结果')
  })

  it('挂载时调用 getWorkOrderDetail', async () => {
    mountDetail()
    await flushPromises()
    expect(mockGetWorkOrderDetail).toHaveBeenCalledWith(1)
  })

  it('加载工单详情后自动检索知识库', async () => {
    mountDetail()
    await flushPromises()
    expect(mockQueryQA).toHaveBeenCalled()
  })

  it('加载失败时提示错误', async () => {
    mockGetWorkOrderDetail.mockRejectedValueOnce(new Error('fail'))
    mountDetail()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载工单详情失败')
  })

  it('点击快捷模板后办结调用 replyWorkOrder', async () => {
    const wrapper = mountDetail()
    await flushPromises()
    mockReplyWorkOrder.mockClear()
    const templateBtn = wrapper.findAll('button').find((b) => b.text() === '已解决')!
    await templateBtn.trigger('click')
    const finishBtn = wrapper.findAll('button').find((b) => b.text() === '办结工单')!
    await finishBtn.trigger('click')
    await flushPromises()
    expect(mockReplyWorkOrder).toHaveBeenCalledWith(1, {
      handle_remark: '问题已核实并处理完成，已通知客户确认。',
    })
    expect(mockElMessage.success).toHaveBeenCalledWith('工单办结完成')
  })

  it('未填备注点击办结提示警告', async () => {
    const wrapper = mountDetail()
    await flushPromises()
    const finishBtn = wrapper.findAll('button').find((b) => b.text() === '办结工单')!
    await finishBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.warning).toHaveBeenCalledWith('办结前请先填写处理备注')
    expect(mockReplyWorkOrder).not.toHaveBeenCalled()
  })

  it('办结失败提示错误', async () => {
    mockReplyWorkOrder.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mountDetail()
    await flushPromises()
    const templateBtn = wrapper.findAll('button').find((b) => b.text() === '已解决')!
    await templateBtn.trigger('click')
    const finishBtn = wrapper.findAll('button').find((b) => b.text() === '办结工单')!
    await finishBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('办结失败')
  })

  it('知识库检索失败提示错误', async () => {
    mockQueryQA.mockRejectedValueOnce(new Error('fail'))
    mountDetail()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('知识库检索失败')
  })

  it('手动输入问题后点重新搜索调用 queryQA 带参数', async () => {
    const wrapper = mountDetail()
    await flushPromises()
    mockQueryQA.mockClear()
    const kbInput = wrapper
      .findAllComponents({ name: 'ElInput' })
      .find((c) => (c.props('placeholder') || '').includes('输入问题搜索知识库'))!
    await kbInput.vm.$emit('update:modelValue', '退款流程')
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '重新搜索')!
    await searchBtn.trigger('click')
    await flushPromises()
    expect(mockQueryQA).toHaveBeenCalledWith({ question: '退款流程' })
  })

  it('点击填入备注按钮填充 remarkText 并提示', async () => {
    mockQueryQA.mockResolvedValueOnce({
      candidates: [{ qa_id: 1, question: 'Q', answer: '答案A', score: 0.9, category_l1: '售后' }],
      confidence: 'high',
    })
    const wrapper = mountDetail()
    await flushPromises()
    const useBtn = wrapper.findAll('button').find((b) => b.text() === '填入备注')!
    await useBtn.trigger('click')
    expect(mockElMessage.success).toHaveBeenCalledWith('已填入处理备注')
  })

  it('点击复制答案按钮调用剪贴板并提示成功', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    mockQueryQA.mockResolvedValueOnce({
      candidates: [{ qa_id: 1, question: 'Q', answer: '答案A', score: 0.9, category_l1: '售后' }],
      confidence: 'high',
    })
    const wrapper = mountDetail()
    await flushPromises()
    const copyBtn = wrapper.findAll('button').find((b) => b.text().includes('复制答案'))!
    await copyBtn.trigger('click')
    await flushPromises()
    expect(writeText).toHaveBeenCalledWith('答案A')
    expect(mockElMessage.success).toHaveBeenCalledWith('已复制到剪贴板')
  })
})
