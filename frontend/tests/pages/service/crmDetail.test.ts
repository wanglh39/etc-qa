import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockRouterPush,
  mockRouterBack,
  mockElMessage,
  mockGetWorkOrderDetail,
  mockReplyWorkOrder,
  mockRouteId,
} = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockRouterBack: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockGetWorkOrderDetail: vi.fn(),
  mockReplyWorkOrder: vi.fn(),
  mockRouteId: { value: '1' },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush, back: mockRouterBack }),
  useRoute: () => ({ query: { id: mockRouteId.value } }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElForm: commonStubs.ElForm,
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()), alert: vi.fn(() => Promise.resolve()) },
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => ({ ...iconStubs }))

vi.mock('@/api/workorder', () => ({
  getWorkOrderDetail: mockGetWorkOrderDetail,
  replyWorkOrder: mockReplyWorkOrder,
}))

import CrmDetail from '@/pages/service/crmDetail.vue'

const stubs = {
  ...commonStubs,
  ...iconStubs,
  ElFormItem: {
    name: 'ElFormItem',
    props: ['prop', 'label', 'required'],
    template:
      '<div class="el-form-item-stub"><span class="form-label">{{ label }}</span><slot></slot></div>',
  },
  ElDescriptionsItem: {
    name: 'ElDescriptionsItem',
    props: ['label', 'span'],
    template:
      '<div class="el-descriptions-item-stub"><span class="desc-label">{{ label }}</span><slot></slot></div>',
  },
}

const interactiveFormStub = (pass: boolean) => ({
  name: 'ElForm',
  props: ['model', 'labelWidth', 'size', 'rules'],
  setup(_: any, { expose }: any) {
    expose({
      validate: (cb: any) => {
        if (typeof cb === 'function') cb(pass)
        return Promise.resolve(pass)
      },
      resetFields: () => {},
    })
  },
  template: '<form class="el-form-stub"><slot></slot></form>',
})

const orderDetail = {
  id: 1,
  external_id: 'W20240101001',
  status: 'submitted',
  dept: 'aftersale',
  service_id: 'S001',
  customer_name: '张三',
  phone: '13800138000',
  problem_type: 'consult',
  next_dept: 'aftersale',
  priority: 'mid',
  detail_desc: '产品咨询问题',
  handle_remark: '',
}

describe('crmDetail', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockRouteId.value = '1'
    mockGetWorkOrderDetail.mockResolvedValue(orderDetail)
    mockReplyWorkOrder.mockResolvedValue({})
  })

  it('渲染返回按钮与页面标题', async () => {
    const wrapper = mount(CrmDetail, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('返回我的待办工单列表')
    expect(text).toContain('业务部门工单处理回复页')
  })

  it('渲染工单原始信息描述项标签', async () => {
    const wrapper = mount(CrmDetail, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('发起客服ID')
    expect(text).toContain('客户名称')
    expect(text).toContain('客户手机号')
    expect(text).toContain('问题分类')
    expect(text).toContain('转交本处理部门')
    expect(text).toContain('工单优先级')
    expect(text).toContain('客户原始问题描述')
    expect(text).toContain('工单状态')
  })

  it('渲染处理回复表单与按钮', async () => {
    const wrapper = mount(CrmDetail, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('业务部门处理回复')
    expect(text).toContain('提交处理回复')
    expect(text).toContain('取消，返回列表')
  })

  it('挂载时调用 getWorkOrderDetail', async () => {
    mount(CrmDetail, { global: { stubs } })
    await flushPromises()
    expect(mockGetWorkOrderDetail).toHaveBeenCalledWith(1)
  })

  it('渲染工单原始信息数据', async () => {
    const wrapper = mount(CrmDetail, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('S001')
    expect(text).toContain('张三')
    expect(text).toContain('13800138000')
    expect(text).toContain('产品咨询问题')
  })

  it('渲染状态映射文本 已提交', async () => {
    const wrapper = mount(CrmDetail, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('已提交')
  })

  it('加载失败时提示错误', async () => {
    mockGetWorkOrderDetail.mockRejectedValueOnce(new Error('fail'))
    mount(CrmDetail, { global: { stubs } })
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载工单详情失败')
  })

  it('提交处理回复成功调用 replyWorkOrder 并跳转列表', async () => {
    const wrapper = mount(CrmDetail, {
      global: { stubs: { ...stubs, ElForm: interactiveFormStub(true) } },
    })
    await flushPromises()
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交处理回复'))!
    await submitBtn.trigger('click')
    await flushPromises()
    expect(mockReplyWorkOrder).toHaveBeenCalledWith(1, { handle_remark: '' })
    expect(mockElMessage.success).toHaveBeenCalledWith('处理回复提交成功')
    expect(mockRouterPush).toHaveBeenCalledWith('/crm/list')
  })

  it('提交处理回复失败提示错误', async () => {
    mockReplyWorkOrder.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(CrmDetail, {
      global: { stubs: { ...stubs, ElForm: interactiveFormStub(true) } },
    })
    await flushPromises()
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交处理回复'))!
    await submitBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('提交处理回复失败')
  })

  it('回复校验失败不调用 replyWorkOrder', async () => {
    const wrapper = mount(CrmDetail, {
      global: { stubs: { ...stubs, ElForm: interactiveFormStub(false) } },
    })
    await flushPromises()
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交处理回复'))!
    await submitBtn.trigger('click')
    await flushPromises()
    expect(mockReplyWorkOrder).not.toHaveBeenCalled()
  })

  it('缺少工单ID时提示错误', async () => {
    mockRouteId.value = ''
    mount(CrmDetail, { global: { stubs } })
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('缺少工单ID')
  })

  it('点击返回按钮调用 router.back', async () => {
    const wrapper = mount(CrmDetail, {
      global: {
        stubs,
        config: { globalProperties: { $router: { push: mockRouterPush, back: mockRouterBack } } },
      },
    })
    await flushPromises()
    const backBtn = wrapper
      .findAll('button')
      .find((b) => b.text().includes('返回我的待办工单列表'))!
    await backBtn.trigger('click')
    expect(mockRouterBack).toHaveBeenCalled()
  })
})
