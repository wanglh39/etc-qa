import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h, ref } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockElMessage,
  mockQueryQA,
  mockGetAsrHealth,
  mockCreateWorkOrder,
  mockGetCategories,
  mockUseStreamingASR,
} = vi.hoisted(() => ({
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockQueryQA: vi.fn(),
  mockGetAsrHealth: vi.fn(),
  mockCreateWorkOrder: vi.fn(),
  mockGetCategories: vi.fn(),
  mockUseStreamingASR: vi.fn(() => ({
    isRecording: ref(false),
    isConnected: ref(false),
    partialText: ref(''),
    fullText: ref(''),
    queryResult: ref(null),
    asrState: ref('IDLE'),
    errorMsg: ref(''),
    startRecording: vi.fn(() => Promise.resolve()),
    stopRecording: vi.fn(),
    disconnect: vi.fn(),
    reset: vi.fn(),
    connect: vi.fn(() => Promise.resolve()),
  })),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), back: vi.fn() }),
  useRoute: () => ({ query: {} }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()), alert: vi.fn(() => Promise.resolve()) },
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => ({
  ...iconStubs,
  Microphone: defineComponent({ name: 'Microphone', render: () => h('span') }),
  CopyDocument: defineComponent({ name: 'CopyDocument', render: () => h('span') }),
  Files: defineComponent({ name: 'Files', render: () => h('span') }),
  VideoPause: defineComponent({ name: 'VideoPause', render: () => h('span') }),
  VideoPlay: defineComponent({ name: 'VideoPlay', render: () => h('span') }),
}))

vi.mock('@/api/workbench', () => ({
  queryQA: mockQueryQA,
  getAsrHealth: mockGetAsrHealth,
}))

vi.mock('@/api/workorder', () => ({
  createWorkOrder: mockCreateWorkOrder,
}))

vi.mock('@/api/knowledge', () => ({
  getCategories: mockGetCategories,
}))

vi.mock('@/composables/useStreamingASR', () => ({
  useStreamingASR: mockUseStreamingASR,
}))

import ServiceIndex from '@/pages/service/index.vue'

const stubs = {
  ...commonStubs,
  ...iconStubs,
  ElCollapse: {
    name: 'ElCollapse',
    props: ['modelValue'],
    template: '<div class="el-collapse-stub"><slot></slot></div>',
  },
  ElCollapseItem: {
    name: 'ElCollapseItem',
    props: ['title', 'name'],
    template:
      '<div class="el-collapse-item-stub"><span class="collapse-title">{{ title }}</span><slot></slot></div>',
  },
}

describe('serviceIndex', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetCategories.mockResolvedValue({ categories: [] })
    mockGetAsrHealth.mockResolvedValue({ loaded: true })
    mockQueryQA.mockResolvedValue({
      query: '',
      standardized_query: '',
      confidence: 'none',
      candidates: [],
      total_candidates: 0,
    })
    mockCreateWorkOrder.mockResolvedValue({ id: 1 })
  })

  it('渲染左栏标题 快捷话术 与 知识库分类', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('快捷话术')
    expect(text).toContain('知识库分类')
  })

  it('渲染快捷话术分组标题', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('感谢语')
    expect(text).toContain('安抚语')
    expect(text).toContain('引导语')
    expect(text).toContain('结束语')
  })

  it('渲染主区标题 客服工作台 与操作按钮', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('客服工作台')
    expect(text).toContain('创建工单')
    expect(text).toContain('搜索')
    expect(text).toContain('清空')
  })

  it('渲染空状态提示文本', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('输入客户问题搜索匹配话术')
  })

  it('渲染工单弹窗问题分类选项', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('产品咨询')
    expect(text).toContain('售后退换')
    expect(text).toContain('系统故障')
    expect(text).toContain('投诉建议')
  })

  it('渲染工单弹窗转交部门选项', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('售后处理部')
    expect(text).toContain('技术运维部')
    expect(text).toContain('财务部')
    expect(text).toContain('市场部')
    expect(text).toContain('人事部')
  })

  it('渲染工单弹窗优先级与底部按钮', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('低')
    expect(text).toContain('中等')
    expect(text).toContain('紧急')
    expect(text).toContain('取消')
    expect(text).toContain('提交工单')
  })

  it('挂载时调用 getCategories 与 getAsrHealth', async () => {
    mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    expect(mockGetCategories).toHaveBeenCalled()
    expect(mockGetAsrHealth).toHaveBeenCalled()
  })

  it('点击创建工单按钮设置弹窗可见', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const createBtn = buttons.find((b) => b.text().includes('创建工单'))
    await createBtn!.trigger('click')
    const dialog = wrapper.findComponent({ name: 'ElDialog' })
    expect(dialog.props('modelValue')).toBe(true)
  })

  it('点击快捷话术项触发插入提示', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const replyItems = wrapper.findAll('.reply-item')
    expect(replyItems.length).toBeGreaterThan(0)
    await replyItems[0].trigger('click')
    expect(mockElMessage.success).toHaveBeenCalledWith('已插入话术')
  })

  it('空搜索时提示请输入问题', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const searchBtn = buttons.find((b) => b.text() === '搜索')
    await searchBtn!.trigger('click')
    expect(mockElMessage.warning).toHaveBeenCalledWith('请输入问题')
  })

  it('输入问题后搜索调用 queryQA', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const searchInput = inputs.find((c) => (c.props('placeholder') || '').includes('输入或粘贴'))
    await searchInput!.vm.$emit('update:modelValue', '如何申请退款')
    const buttons = wrapper.findAll('button')
    const searchBtn = buttons.find((b) => b.text() === '搜索')
    await searchBtn!.trigger('click')
    await flushPromises()
    expect(mockQueryQA).toHaveBeenCalled()
  })

  it('打开工单弹窗并提交调用 createWorkOrder', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const createBtn = buttons.find((b) => b.text().includes('创建工单'))
    await createBtn!.trigger('click')
    await flushPromises()
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交工单'))
    await submitBtn!.trigger('click')
    await flushPromises()
    expect(mockCreateWorkOrder).toHaveBeenCalled()
  })

  it('点击清空按钮调用 asr.reset', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    const buttons = wrapper.findAll('button')
    const clearBtn = buttons.find((b) => b.text() === '清空')
    await clearBtn!.trigger('click')
    expect(asrInstance.reset).toHaveBeenCalled()
  })

  it('搜索有结果后点击候选触发选择', async () => {
    mockQueryQA.mockResolvedValueOnce({
      query: '如何退款',
      standardized_query: '如何退款',
      confidence: 'high',
      candidates: [
        { qa_id: 1, question: '如何退款', answer: '请联系客服', score: 0.9, category_l1: '售后' },
      ],
      total_candidates: 1,
    })
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const searchInput = inputs.find((c) => (c.props('placeholder') || '').includes('输入或粘贴'))
    await searchInput!.vm.$emit('update:modelValue', '如何申请退款')
    const buttons = wrapper.findAll('button')
    const searchBtn = buttons.find((b) => b.text() === '搜索')
    await searchBtn!.trigger('click')
    await flushPromises()
    const selectBtn = wrapper.findAll('button').find((b) => b.text() === '选择')
    expect(selectBtn).toBeTruthy()
    await selectBtn!.trigger('click')
    const selectedBtn = wrapper.findAll('button').find((b) => b.text() === '已选')
    expect(selectedBtn).toBeTruthy()
  })

  it('点击录音按钮启动录音调用 startRecording', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    const recordBtn = wrapper.findAll('button').find((b) => b.text() === '')!
    expect(recordBtn).toBeTruthy()
    await recordBtn.trigger('click')
    await flushPromises()
    expect(asrInstance.startRecording).toHaveBeenCalled()
  })

  it('搜索失败提示查询失败', async () => {
    mockQueryQA.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const searchInput = inputs.find((c) => (c.props('placeholder') || '').includes('输入或粘贴'))!
    await searchInput.vm.$emit('update:modelValue', '如何申请退款')
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索')!
    await searchBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('查询失败')
  })

  it('工单提交失败提示错误', async () => {
    mockCreateWorkOrder.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const createBtn = wrapper.findAll('button').find((b) => b.text().includes('创建工单'))!
    await createBtn.trigger('click')
    await flushPromises()
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交工单'))!
    await submitBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('工单提交失败')
  })

  it('搜索问题过短提示无意义', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const searchInput = inputs.find((c) => (c.props('placeholder') || '').includes('输入或粘贴'))!
    await searchInput.vm.$emit('update:modelValue', '啊')
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索')!
    await searchBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.warning).toHaveBeenCalledWith('问题文本过短或无意义，请编辑后重试')
  })

  it('录音启动失败提示权限错误', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    asrInstance.startRecording.mockRejectedValueOnce(new Error('NotAllowed'))
    const recordBtn = wrapper.findAll('button').find((b) => b.text() === '')!
    await recordBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith(
      '麦克风权限被拒绝，请在浏览器设置中允许访问麦克风后重试'
    )
  })

  it('ASR健康检查失败时不渲染ASR状态标签', async () => {
    mockGetAsrHealth.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    expect(mockGetAsrHealth).toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('ASR 已就绪')
    expect(wrapper.text()).not.toContain('ASR 待加载')
  })

  it('点击候选复制按钮调用剪贴板并提示成功', async () => {
    const writeText = vi.fn(() => Promise.resolve())
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    mockQueryQA.mockResolvedValueOnce({
      query: '如何退款',
      standardized_query: '如何退款',
      confidence: 'high',
      candidates: [
        { qa_id: 1, question: '如何退款', answer: '请联系客服', score: 0.9, category_l1: '售后' },
      ],
      total_candidates: 1,
    })
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const searchInput = inputs.find((c) => (c.props('placeholder') || '').includes('输入或粘贴'))!
    await searchInput.vm.$emit('update:modelValue', '如何申请退款')
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索')!
    await searchBtn.trigger('click')
    await flushPromises()
    const copyBtn = wrapper.findAll('button').find((b) => b.text() === '复制')!
    await copyBtn.trigger('click')
    await flushPromises()
    expect(writeText).toHaveBeenCalledWith('请联系客服')
    expect(mockElMessage.success).toHaveBeenCalledWith('已复制到剪贴板')
  })

  it('点击分类节点设置分类筛选', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const tree = wrapper.findComponent({ name: 'ElTree' })
    await tree.vm.$emit('node-click', { label: '售后' })
    expect(wrapper.text()).toContain('分类筛选')
    expect(wrapper.text()).toContain('售后')
  })

  it('录音后点击停止调用 stopRecording 与 disconnect', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    const recordBtn = wrapper.findAll('button').find((b) => b.text() === '')!
    await recordBtn.trigger('click')
    await flushPromises()
    const emptyBtns = wrapper.findAll('button').filter((b) => b.text() === '')
    const stopBtn = emptyBtns[emptyBtns.length - 1]
    await stopBtn.trigger('click')
    expect(asrInstance.stopRecording).toHaveBeenCalled()
    expect(asrInstance.disconnect).toHaveBeenCalled()
  })

  it('点击清除分类筛选重置选中分类', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const tree = wrapper.findComponent({ name: 'ElTree' })
    await tree.vm.$emit('node-click', { label: '售后' })
    await flushPromises()
    expect(wrapper.text()).toContain('分类筛选')
    const clearBtn = wrapper.findAll('button').find((b) => b.text().includes('清除分类筛选'))!
    await clearBtn.trigger('click')
    expect(wrapper.text()).not.toContain('分类筛选')
  })

  it('工单表单校验异常提示完善信息', async () => {
    const formStub = {
      ...commonStubs.ElForm,
      setup(_: any, { expose }: any) {
        expose({ validate: () => Promise.reject(new Error('fail')), resetFields: () => {} })
      },
    }
    const wrapper = mount(ServiceIndex, { global: { stubs: { ...stubs, ElForm: formStub } } })
    await flushPromises()
    const createBtn = wrapper.findAll('button').find((b) => b.text().includes('创建工单'))!
    await createBtn.trigger('click')
    await flushPromises()
    const submitBtn = wrapper.findAll('button').find((b) => b.text().includes('提交工单'))!
    await submitBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.warning).toHaveBeenCalledWith('请完善全部必填信息后再提交')
  })

  it('录音暂停后点击继续再次调用 startRecording', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    const recordBtn = wrapper.findAll('button').find((b) => b.text() === '')!
    await recordBtn.trigger('click')
    await flushPromises()
    const emptyBtns = wrapper.findAll('button').filter((b) => b.text() === '')
    await emptyBtns[0].trigger('click')
    await flushPromises()
    const resumeBtn = wrapper.findAll('button').filter((b) => b.text() === '')[0]
    await resumeBtn.trigger('click')
    await flushPromises()
    expect(asrInstance.startRecording).toHaveBeenCalledTimes(2)
  })

  it('录音有文本时暂停填充搜索框', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    const recordBtn = wrapper.findAll('button').find((b) => b.text() === '')!
    await recordBtn.trigger('click')
    await flushPromises()
    asrInstance.fullText.value = '客户问题文本内容'
    const emptyBtns = wrapper.findAll('button').filter((b) => b.text() === '')
    await emptyBtns[0].trigger('click')
    expect(asrInstance.stopRecording).toHaveBeenCalled()
  })

  it('录音继续失败提示 WebSocket 错误', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    const recordBtn = wrapper.findAll('button').find((b) => b.text() === '')!
    await recordBtn.trigger('click')
    await flushPromises()
    const emptyBtns = wrapper.findAll('button').filter((b) => b.text() === '')
    await emptyBtns[0].trigger('click')
    await flushPromises()
    asrInstance.startRecording.mockRejectedValueOnce(new Error('WebSocket'))
    const resumeBtn = wrapper.findAll('button').filter((b) => b.text() === '')[0]
    await resumeBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('WebSocket连接失败，请确认后端服务已启动')
  })

  it('录音有文本时停止填充搜索框', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    const recordBtn = wrapper.findAll('button').find((b) => b.text() === '')!
    await recordBtn.trigger('click')
    await flushPromises()
    asrInstance.fullText.value = '客户问题文本内容'
    const emptyBtns = wrapper.findAll('button').filter((b) => b.text() === '')
    await emptyBtns[emptyBtns.length - 1].trigger('click')
    expect(asrInstance.stopRecording).toHaveBeenCalled()
    expect(asrInstance.disconnect).toHaveBeenCalled()
  })

  it('录音启动失败未知错误提示通用失败', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    asrInstance.startRecording.mockRejectedValueOnce(new Error('unknown'))
    const recordBtn = wrapper.findAll('button').find((b) => b.text() === '')!
    await recordBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('录音启动失败: unknown')
  })

  it('搜索结果低分候选渲染低分色', async () => {
    mockQueryQA.mockResolvedValueOnce({
      query: 'q',
      standardized_query: 'q',
      confidence: 'low',
      candidates: [{ qa_id: 1, question: 'q', answer: 'a', score: 0.5, category_l1: 'c' }],
      total_candidates: 1,
    })
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const searchInput = inputs.find((c) => (c.props('placeholder') || '').includes('输入或粘贴'))!
    await searchInput.vm.$emit('update:modelValue', '如何申请退款')
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索')!
    await searchBtn.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('50.0%')
  })

  it('再次点击已选候选取消选择', async () => {
    mockQueryQA.mockResolvedValueOnce({
      query: 'q',
      standardized_query: 'q',
      confidence: 'high',
      candidates: [{ qa_id: 1, question: 'q', answer: 'a', score: 0.9, category_l1: 'c' }],
      total_candidates: 1,
    })
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const searchInput = inputs.find((c) => (c.props('placeholder') || '').includes('输入或粘贴'))!
    await searchInput.vm.$emit('update:modelValue', '如何申请退款')
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索')!
    await searchBtn.trigger('click')
    await flushPromises()
    const selectBtn = wrapper.findAll('button').find((b) => b.text() === '选择')!
    await selectBtn.trigger('click')
    const selectedBtn = wrapper.findAll('button').find((b) => b.text() === '已选')!
    await selectedBtn.trigger('click')
    expect(wrapper.findAll('button').find((b) => b.text() === '选择')).toBeTruthy()
  })

  it('录音启动失败非安全上下文提示原消息', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    asrInstance.startRecording.mockRejectedValueOnce(new Error('非安全上下文'))
    const recordBtn = wrapper.findAll('button').find((b) => b.text() === '')!
    await recordBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('非安全上下文')
  })

  it('录音启动失败未检测到麦克风提示', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const asrInstance = mockUseStreamingASR.mock.results[0].value
    asrInstance.startRecording.mockRejectedValueOnce(new Error('NotFound'))
    const recordBtn = wrapper.findAll('button').find((b) => b.text() === '')!
    await recordBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('未检测到麦克风设备，请确认麦克风已连接')
  })

  it('有搜索文本时点击分类触发搜索', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const searchInput = inputs.find((c) => (c.props('placeholder') || '').includes('输入或粘贴'))!
    await searchInput.vm.$emit('update:modelValue', '如何申请退款')
    const tree = wrapper.findComponent({ name: 'ElTree' })
    await tree.vm.$emit('node-click', { label: '售后' })
    await flushPromises()
    expect(mockQueryQA).toHaveBeenCalled()
  })

  it('有搜索文本时清除分类触发搜索', async () => {
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const searchInput = inputs.find((c) => (c.props('placeholder') || '').includes('输入或粘贴'))!
    await searchInput.vm.$emit('update:modelValue', '如何申请退款')
    const tree = wrapper.findComponent({ name: 'ElTree' })
    await tree.vm.$emit('node-click', { label: '售后' })
    await flushPromises()
    mockQueryQA.mockClear()
    const clearBtn = wrapper.findAll('button').find((b) => b.text().includes('清除分类筛选'))!
    await clearBtn.trigger('click')
    await flushPromises()
    expect(mockQueryQA).toHaveBeenCalled()
  })

  it('复制失败提示错误', async () => {
    const writeText = vi.fn(() => Promise.reject(new Error('fail')))
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    mockQueryQA.mockResolvedValueOnce({
      query: 'q',
      standardized_query: 'q',
      confidence: 'high',
      candidates: [{ qa_id: 1, question: 'q', answer: 'a', score: 0.9, category_l1: 'c' }],
      total_candidates: 1,
    })
    const wrapper = mount(ServiceIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const searchInput = inputs.find((c) => (c.props('placeholder') || '').includes('输入或粘贴'))!
    await searchInput.vm.$emit('update:modelValue', '如何申请退款')
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索')!
    await searchBtn.trigger('click')
    await flushPromises()
    const copyBtn = wrapper.findAll('button').find((b) => b.text() === '复制')!
    await copyBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('复制失败，请手动选择复制')
  })

  it('分类筛选输入触发节点过滤', async () => {
    const filterStub = {
      name: 'ElTree',
      props: ['data', 'props', 'nodeKey', 'filterNodeMethod'],
      setup(props: any, { expose }: any) {
        expose({
          filter: (val: string) => {
            if (val && props.data) {
              props.data.forEach((node: any) => props.filterNodeMethod?.(val, node))
            }
          },
        })
      },
      template: '<div class="el-tree-stub"></div>',
    }
    mockGetCategories.mockResolvedValueOnce({
      categories: [{ id: 1, label: '售后', parent_id: 0 }],
    })
    const wrapper = mount(ServiceIndex, { global: { stubs: { ...stubs, ElTree: filterStub } } })
    await flushPromises()
    const filterInput = wrapper
      .findAllComponents({ name: 'ElInput' })
      .find((c) => (c.props('placeholder') || '').includes('搜索分类'))!
    await filterInput.vm.$emit('update:modelValue', '售')
    await flushPromises()
    expect(wrapper.text()).toContain('知识库分类')
  })
})
