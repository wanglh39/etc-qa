import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockElMessage,
  mockElMessageBox,
  mockGetQAList,
  mockSearchQA,
  mockGetQADetail,
  mockAddQA,
  mockUpdateQA,
  mockUpdateQAStatus,
  mockDeleteQA,
  mockGetCategories,
} = vi.hoisted(() => ({
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(() => Promise.resolve()),
  },
  mockGetQAList: vi.fn(),
  mockSearchQA: vi.fn(),
  mockGetQADetail: vi.fn(),
  mockAddQA: vi.fn(),
  mockUpdateQA: vi.fn(),
  mockUpdateQAStatus: vi.fn(),
  mockDeleteQA: vi.fn(),
  mockGetCategories: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ query: {} }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: mockElMessageBox,
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => ({ ...iconStubs }))

vi.mock('@/api/knowledge', () => ({
  getQAList: mockGetQAList,
  searchQA: mockSearchQA,
  getQADetail: mockGetQADetail,
  addQA: mockAddQA,
  updateQA: mockUpdateQA,
  updateQAStatus: mockUpdateQAStatus,
  deleteQA: mockDeleteQA,
  getCategories: mockGetCategories,
}))

import KnowledgeList from '@/pages/knowledge/list.vue'

const tableColStub = {
  name: 'ElTableColumn',
  props: ['type', 'width', 'prop', 'label', 'fixed', 'align', 'minWidth', 'showOverflowTooltip'],
  template:
    "<div class=\"el-table-col-stub\">{{ label }}<slot :row=\"{ id: 1, status: 'deprecated', question: 'q', answer: 'a', category_l1: '', category_l2: '', updated_at: '' }\" /></div>",
}
const stubs = { ...commonStubs, ...iconStubs, ElTableColumn: tableColStub }

const qaList = {
  items: [
    {
      id: 1,
      question: '如何退款',
      answer: '请联系客服',
      category_l1: '售后',
      category_l2: '',
      status: 'active',
      updated_at: '2024-01-01',
    },
    {
      id: 2,
      question: '如何下单',
      answer: '点击购买',
      category_l1: '产品',
      category_l2: '',
      status: 'deprecated',
      updated_at: '2024-01-02',
    },
  ],
  total: 2,
}

describe('knowledgeList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetQAList.mockResolvedValue(qaList)
    mockGetCategories.mockResolvedValue({ categories: [{ label: '售后', children: [] }] })
    mockAddQA.mockResolvedValue({})
    mockUpdateQA.mockResolvedValue({})
    mockUpdateQAStatus.mockResolvedValue({})
    mockDeleteQA.mockResolvedValue({})
    mockGetQADetail.mockResolvedValue({
      id: 1,
      question: 'q',
      answer: 'a',
      category_l1: '',
      category_l2: '',
      internal_process: '',
      feedback_dept: '',
      status: 'active',
      created_at: '',
      updated_at: '',
    })
  })

  it('渲染页面标题 知识库管理', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    expect(wrapper.text()).toContain('知识库管理')
  })

  it('渲染筛选区按钮 搜索 重置 新增知识', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('搜索')
    expect(text).toContain('重置')
    expect(text).toContain('新增知识')
  })

  it('渲染批量操作按钮', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('批量上架')
    expect(text).toContain('批量下架')
    expect(text).toContain('批量删除')
  })

  it('渲染表格列头', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('ID')
    expect(text).toContain('问题内容')
    expect(text).toContain('答案摘要')
    expect(text).toContain('分类')
    expect(text).toContain('更新时间')
    expect(text).toContain('操作')
  })

  it('渲染表格与分页组件', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    expect(wrapper.find('.el-table-stub').exists()).toBe(true)
    expect(wrapper.find('.el-pagination-stub').exists()).toBe(true)
  })

  it('挂载时调用 getQAList 与 getCategories', async () => {
    mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    expect(mockGetQAList).toHaveBeenCalled()
    expect(mockGetCategories).toHaveBeenCalled()
  })

  it('加载列表失败时提示错误', async () => {
    mockGetQAList.mockRejectedValueOnce(new Error('fail'))
    mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载知识列表失败')
  })

  it('点击新增知识弹出对话框含表单', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const addBtn = buttons.find((b) => b.text().includes('新增知识'))
    await addBtn!.trigger('click')
    await flushPromises()
    const dialogs = wrapper.findAllComponents({ name: 'ElDialog' })
    expect(dialogs.length).toBeGreaterThanOrEqual(1)
    expect(dialogs.some((d) => d.props('title') === '新增知识')).toBe(true)
    expect(wrapper.findAll('.el-form-stub').length).toBeGreaterThanOrEqual(1)
  })

  it('点击重置按钮重新加载列表', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const callsBefore = mockGetQAList.mock.calls.length
    const buttons = wrapper.findAll('button')
    const resetBtn = buttons.find((b) => b.text().includes('重置'))
    await resetBtn!.trigger('click')
    await flushPromises()
    expect(mockGetQAList.mock.calls.length).toBeGreaterThan(callsBefore)
  })

  it('未勾选时批量上架提示警告', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const batchBtn = buttons.find((b) => b.text() === '批量上架')
    await batchBtn!.trigger('click')
    expect(mockElMessage.warning).toHaveBeenCalledWith('请先勾选要上架的条目')
  })

  it('未勾选时批量删除提示警告', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const batchBtn = buttons.find((b) => b.text() === '批量删除')
    await batchBtn!.trigger('click')
    expect(mockElMessage.warning).toHaveBeenCalledWith('请先勾选要删除的条目')
  })

  it('点击搜索按钮重新加载列表', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    mockGetQAList.mockClear()
    const buttons = wrapper.findAll('button')
    const searchBtn = buttons.find((b) => b.text() === '搜索')
    await searchBtn!.trigger('click')
    await flushPromises()
    expect(mockGetQAList).toHaveBeenCalled()
  })

  it('点击查看详情调用 getQADetail', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const detailBtn = buttons.find((b) => b.text() === '查看详情')
    await detailBtn!.trigger('click')
    await flushPromises()
    expect(mockGetQADetail).toHaveBeenCalledWith(1)
  })

  it('新增知识填写后提交调用 addQA', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const addBtn = buttons.find((b) => b.text().includes('新增知识'))
    await addBtn!.trigger('click')
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const qInput = inputs.find((c) => (c.props('placeholder') || '').includes('标准化问题'))
    const aInput = inputs.find((c) => (c.props('placeholder') || '').includes('标准解决方案'))
    await qInput!.vm.$emit('update:modelValue', '测试问题')
    await aInput!.vm.$emit('update:modelValue', '测试答案')
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认新增')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockAddQA).toHaveBeenCalled()
  })

  it('点击上架调用 updateQAStatus', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    mockUpdateQAStatus.mockClear()
    const buttons = wrapper.findAll('button')
    const upBtn = buttons.find((b) => b.text() === '上架')
    await upBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateQAStatus).toHaveBeenCalledWith(1, 'active')
  })

  it('点击删除调用 deleteQA', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    mockDeleteQA.mockClear()
    const buttons = wrapper.findAll('button')
    const delBtn = buttons.find((b) => b.text() === '删除')
    await delBtn!.trigger('click')
    await flushPromises()
    expect(mockDeleteQA).toHaveBeenCalledWith(1)
  })

  it('点击编辑打开编辑对话框', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const editBtn = buttons.find((b) => b.text() === '编辑')
    await editBtn!.trigger('click')
    await flushPromises()
    const dialogs = wrapper.findAllComponents({ name: 'ElDialog' })
    expect(dialogs.some((d) => d.props('title') === '编辑知识')).toBe(true)
  })

  it('输入关键词后搜索调用 searchQA 带参数', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    mockSearchQA.mockClear()
    const keywordInput = wrapper
      .findAllComponents({ name: 'ElInput' })
      .find((c) => (c.props('placeholder') || '').includes('关键词检索'))
    await keywordInput!.vm.$emit('update:modelValue', '退款')
    await flushPromises()
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索')
    await searchBtn!.trigger('click')
    await flushPromises()
    expect(mockSearchQA).toHaveBeenCalledWith({
      keyword: '退款',
      category_l1: undefined,
      status: undefined,
      page: 1,
      page_size: 10,
    })
  })

  it('分页 current-change 切换到第2页带新页码', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    mockGetQAList.mockClear()
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    await pagination.vm.$emit('update:current-page', 2)
    await pagination.vm.$emit('current-change')
    await flushPromises()
    expect(mockGetQAList).toHaveBeenLastCalledWith({
      page: 2,
      page_size: 10,
      category_l1: undefined,
      status: undefined,
    })
  })

  it('删除确认取消时不调用 deleteQA', async () => {
    mockElMessageBox.confirm.mockRejectedValueOnce(new Error('cancel'))
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    mockDeleteQA.mockClear()
    const delBtn = wrapper.findAll('button').find((b) => b.text() === '删除')
    await delBtn!.trigger('click')
    await flushPromises()
    expect(mockDeleteQA).not.toHaveBeenCalled()
  })

  it('编辑对话框点确认编辑调用updateQA并提示成功', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text() === '编辑')
    await editBtn!.trigger('click')
    await flushPromises()
    const confirmEditBtn = wrapper.findAll('button').find((b) => b.text() === '确认编辑')
    await confirmEditBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateQA).toHaveBeenCalled()
    expect(mockElMessage.success).toHaveBeenCalledWith('编辑成功')
  })

  it('新增时未填问题点确认新增提示警告', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增知识'))
    await addBtn!.trigger('click')
    await flushPromises()
    const confirmAddBtn = wrapper.findAll('button').find((b) => b.text() === '确认新增')
    await confirmAddBtn!.trigger('click')
    expect(mockElMessage.warning).toHaveBeenCalledWith('问题内容和标准答案不能为空')
  })

  it('getQADetail 失败提示加载详情失败', async () => {
    mockGetQADetail.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const detailBtn = wrapper.findAll('button').find((b) => b.text() === '查看详情')
    await detailBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载详情失败')
  })

  it('addQA 失败提示新增失败', async () => {
    mockAddQA.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增知识'))
    await addBtn!.trigger('click')
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const qInput = inputs.find((c) => (c.props('placeholder') || '').includes('标准化问题'))
    const aInput = inputs.find((c) => (c.props('placeholder') || '').includes('标准解决方案'))
    await qInput!.vm.$emit('update:modelValue', '问题')
    await aInput!.vm.$emit('update:modelValue', '答案')
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认新增')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('新增失败')
  })

  it('点击上架失败提示上架失败', async () => {
    mockUpdateQAStatus.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const upBtn = wrapper.findAll('button').find((b) => b.text() === '上架')
    await upBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('上架失败')
  })

  it('点击删除失败提示删除失败', async () => {
    mockDeleteQA.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const delBtn = wrapper.findAll('button').find((b) => b.text() === '删除')
    await delBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('删除失败')
  })

  it('getCategories 失败提示加载分类失败', async () => {
    mockGetCategories.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载分类失败')
  })

  it('勾选后批量上架成功调用 updateQAStatus', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    mockUpdateQAStatus.mockClear()
    const table = wrapper.findComponent({ name: 'ElTable' })
    await table.vm.$emit('selection-change', [{ id: 1 }, { id: 2 }])
    await flushPromises()
    const batchBtn = wrapper.findAll('button').find((b) => b.text() === '批量上架')
    await batchBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateQAStatus).toHaveBeenCalledWith(1, 'active')
    expect(mockUpdateQAStatus).toHaveBeenCalledWith(2, 'active')
    expect(mockElMessage.success).toHaveBeenCalled()
  })

  it('未勾选时批量下架提示警告', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const batchBtn = wrapper.findAll('button').find((b) => b.text() === '批量下架')
    await batchBtn!.trigger('click')
    expect(mockElMessage.warning).toHaveBeenCalledWith('请先勾选要下架的条目')
  })

  it('新增填写完整表单提交带内部流程和反馈部门', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增知识'))
    await addBtn!.trigger('click')
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const qInput = inputs.find((c) => (c.props('placeholder') || '').includes('标准化问题'))
    const aInput = inputs.find((c) => (c.props('placeholder') || '').includes('标准解决方案'))
    const processInput = inputs.find(
      (c) => (c.props('placeholder') || '') === '可选' && (c.props('type') || '') === 'textarea'
    )
    const deptInput = inputs.find(
      (c) => (c.props('placeholder') || '') === '可选' && !c.props('type')
    )
    await qInput!.vm.$emit('update:modelValue', '问题')
    await aInput!.vm.$emit('update:modelValue', '答案')
    await processInput!.vm.$emit('update:modelValue', '流程')
    await deptInput!.vm.$emit('update:modelValue', '部门')
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认新增')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockAddQA).toHaveBeenCalledWith(
      expect.objectContaining({
        question: '问题',
        answer: '答案',
        internal_process: '流程',
        feedback_dept: '部门',
      })
    )
  })

  it('新增对话框点击取消不调用 addQA', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增知识'))
    await addBtn!.trigger('click')
    await flushPromises()
    mockAddQA.mockClear()
    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === '取消')
    await cancelBtn!.trigger('click')
    await flushPromises()
    expect(mockAddQA).not.toHaveBeenCalled()
  })

  it('点击下架调用 updateQAStatus deprecated', async () => {
    const activeStubs = {
      ...stubs,
      ElTableColumn: {
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
        ],
        template:
          "<div class=\"el-table-col-stub\">{{ label }}<slot :row=\"{ id: 1, status: 'active', question: 'q', answer: 'a', category_l1: '', category_l2: '', updated_at: '' }\" /></div>",
      },
    }
    const wrapper = mount(KnowledgeList, { global: { stubs: activeStubs } })
    await flushPromises()
    mockUpdateQAStatus.mockClear()
    const downBtn = wrapper.findAll('button').find((b) => b.text() === '下架')
    await downBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateQAStatus).toHaveBeenCalledWith(1, 'deprecated')
    expect(mockElMessage.success).toHaveBeenCalledWith('下架成功')
  })

  it('选择状态筛选后搜索带 status 参数', async () => {
    const wrapper = mount(KnowledgeList, { global: { stubs } })
    await flushPromises()
    mockGetQAList.mockClear()
    const statusSelect = wrapper
      .findAllComponents({ name: 'ElSelect' })
      .find((s) => (s.props('placeholder') || '') === '状态')
    await statusSelect!.vm.$emit('update:modelValue', 'active')
    await statusSelect!.vm.$emit('change')
    await flushPromises()
    expect(mockGetQAList).toHaveBeenLastCalledWith(expect.objectContaining({ status: 'active' }))
  })
})
