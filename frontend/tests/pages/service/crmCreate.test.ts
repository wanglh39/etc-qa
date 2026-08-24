import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const { mockRouterPush, mockElMessage, mockCreateWorkOrder } = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockCreateWorkOrder: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
  useRoute: () => ({ query: {} }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElForm: commonStubs.ElForm,
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()), alert: vi.fn(() => Promise.resolve()) },
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => ({ ...iconStubs }))

vi.mock('@/api/workorder', () => ({
  createWorkOrder: mockCreateWorkOrder,
}))

import CrmCreate from '@/pages/service/crmCreate.vue'

const stubs = {
  ...commonStubs,
  ...iconStubs,
  ElFormItem: {
    name: 'ElFormItem',
    props: ['prop', 'label', 'required'],
    template:
      '<div class="el-form-item-stub"><span class="form-label">{{ label }}</span><slot></slot></div>',
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

describe('crmCreate', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockCreateWorkOrder.mockResolvedValue({ id: 1 })
  })

  it('渲染页面标题 客服发起CRM工单', () => {
    const wrapper = mount(CrmCreate, { global: { stubs } })
    expect(wrapper.text()).toContain('客服发起CRM工单')
  })

  it('渲染全部表单项标签', () => {
    const wrapper = mount(CrmCreate, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('发起客服ID')
    expect(text).toContain('客户名称')
    expect(text).toContain('客户联系电话')
    expect(text).toContain('客户问题分类')
    expect(text).toContain('转交处理部门')
    expect(text).toContain('工单优先级')
    expect(text).toContain('客户原始问题描述')
  })

  it('渲染提交与重置按钮', () => {
    const wrapper = mount(CrmCreate, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('提交工单，转交对应部门处理')
    expect(text).toContain('重置表单')
  })

  it('渲染问题分类选项', () => {
    const wrapper = mount(CrmCreate, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('产品咨询')
    expect(text).toContain('售后退换')
    expect(text).toContain('系统故障')
    expect(text).toContain('投诉建议')
  })

  it('渲染转交部门选项', () => {
    const wrapper = mount(CrmCreate, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('售后处理部')
    expect(text).toContain('技术运维部')
    expect(text).toContain('财务部')
    expect(text).toContain('市场部')
    expect(text).toContain('人事部')
  })

  it('渲染优先级单选 低 中等 紧急', () => {
    const wrapper = mount(CrmCreate, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('低')
    expect(text).toContain('中等')
    expect(text).toContain('紧急')
  })

  it('渲染表单与表单项组件', () => {
    const wrapper = mount(CrmCreate, { global: { stubs } })
    expect(wrapper.find('.el-form-stub').exists()).toBe(true)
    expect(wrapper.findAll('.el-form-item-stub').length).toBeGreaterThanOrEqual(7)
  })

  it('提交工单成功调用 createWorkOrder 并跳转详情', async () => {
    const wrapper = mount(CrmCreate, {
      global: { stubs: { ...stubs, ElForm: interactiveFormStub(true) } },
    })
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交工单'))!
    await submitBtn.trigger('click')
    await flushPromises()
    expect(mockCreateWorkOrder).toHaveBeenCalled()
    expect(mockElMessage.success).toHaveBeenCalledWith('工单已提交，转交对应业务部门处理')
    expect(mockRouterPush).toHaveBeenCalledWith({ name: 'CrmDetail', query: { id: 1 } })
  })

  it('提交工单失败提示错误', async () => {
    mockCreateWorkOrder.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(CrmCreate, {
      global: { stubs: { ...stubs, ElForm: interactiveFormStub(true) } },
    })
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交工单'))!
    await submitBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('工单提交失败')
  })

  it('表单校验失败提示完善信息且不调用 createWorkOrder', async () => {
    const wrapper = mount(CrmCreate, {
      global: { stubs: { ...stubs, ElForm: interactiveFormStub(false) } },
    })
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交工单'))!
    await submitBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.warning).toHaveBeenCalledWith('请完善全部必填信息后再提交')
    expect(mockCreateWorkOrder).not.toHaveBeenCalled()
  })

  it('点击重置按钮调用 resetFields', async () => {
    const resetFields = vi.fn()
    const formStub = {
      name: 'ElForm',
      props: ['model', 'labelWidth', 'size', 'rules'],
      setup(_: any, { expose }: any) {
        expose({ validate: () => Promise.resolve(true), resetFields })
      },
      template: '<form class="el-form-stub"><slot></slot></form>',
    }
    const wrapper = mount(CrmCreate, { global: { stubs: { ...stubs, ElForm: formStub } } })
    const resetBtn = wrapper.findAll('button').find((b) => b.text().includes('重置表单'))!
    await resetBtn.trigger('click')
    expect(resetFields).toHaveBeenCalled()
  })

  it('填写完整表单后提交传递正确数据', async () => {
    const wrapper = mount(CrmCreate, {
      global: { stubs: { ...stubs, ElForm: interactiveFormStub(true) } },
    })
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    await inputs[0].vm.$emit('update:modelValue', 'S001')
    await inputs[1].vm.$emit('update:modelValue', '张三')
    await inputs[2].vm.$emit('update:modelValue', '13800138000')
    const selects = wrapper.findAllComponents({ name: 'ElSelect' })
    await selects[0].vm.$emit('update:modelValue', 'consult')
    await selects[1].vm.$emit('update:modelValue', 'aftersale')
    const radios = wrapper.findAllComponents({ name: 'ElRadioGroup' })
    await radios[0].vm.$emit('update:modelValue', 'high')
    const detailInput = inputs[inputs.length - 1]
    await detailInput.vm.$emit('update:modelValue', '客户问题详情')
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交工单'))!
    await submitBtn.trigger('click')
    await flushPromises()
    expect(mockCreateWorkOrder).toHaveBeenCalledWith(
      expect.objectContaining({
        service_id: 'S001',
        customer_name: '张三',
        phone: '13800138000',
        problem_type: 'consult',
        next_dept: 'aftersale',
        priority: 'high',
        detail_desc: '客户问题详情',
      })
    )
  })
})
