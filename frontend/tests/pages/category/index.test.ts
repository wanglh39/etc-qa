import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockRouterPush,
  mockElMessage,
  mockElMessageBox,
  mockElNotification,
  mockGetCategories,
  mockCreateCategory,
  mockUpdateCategory,
  mockDeleteCategory,
} = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(() => Promise.resolve()),
  },
  mockElNotification: vi.fn(),
  mockGetCategories: vi.fn(),
  mockCreateCategory: vi.fn(),
  mockUpdateCategory: vi.fn(),
  mockDeleteCategory: vi.fn(),
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
}))

vi.mock('@/api/knowledge', () => ({
  getCategories: mockGetCategories,
  createCategory: mockCreateCategory,
  updateCategory: mockUpdateCategory,
  deleteCategory: mockDeleteCategory,
}))

import CategoryIndex from '@/pages/category/index.vue'

const PageLayoutStub = {
  name: 'PageLayout',
  props: ['pageTitle'],
  template:
    '<div class="page-layout-stub"><div class="page-title">{{ pageTitle }}</div><div class="page-actions"><slot name="actions"></slot></div><div class="page-content"><slot></slot></div></div>',
}

const stubs = {
  ...commonStubs,
  ...iconStubs,
  PageLayout: PageLayoutStub,
  ElTreeSelect: {
    name: 'ElTreeSelect',
    props: ['modelValue', 'data', 'placeholder', 'clearable'],
    emits: ['update:modelValue'],
    template: '<select class="el-tree-select-stub"><slot></slot></select>',
  },
  ElFormItem: {
    name: 'ElFormItem',
    props: ['prop', 'label'],
    template:
      '<div class="el-form-item-stub"><span class="form-label">{{ label }}</span><slot></slot></div>',
  },
}

describe('categoryIndex', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    setActivePinia(createPinia())
    mockGetCategories.mockResolvedValue({ categories: [] })
    mockCreateCategory.mockResolvedValue({})
    mockUpdateCategory.mockResolvedValue({})
    mockDeleteCategory.mockResolvedValue({})
  })

  it('renders 分类管理 title', () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    expect(wrapper.text()).toContain('分类管理')
  })

  it('renders 新增分类 button', () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    expect(wrapper.text()).toContain('新增分类')
  })

  it('renders 分类树 header', () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    expect(wrapper.text()).toContain('分类树')
  })

  it('renders 新增分类 as initial form mode', () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    expect(wrapper.text()).toContain('新增分类')
  })

  it('renders form item labels', () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('分类名称')
    expect(text).toContain('上级分类')
    expect(text).toContain('分类描述')
  })

  it('renders 创建 新建 删除 buttons', () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    const text = wrapper.text()
    expect(text).toContain('创建')
    expect(text).toContain('新建')
    expect(text).toContain('删除')
  })

  it('calls getCategories on mount', () => {
    mount(CategoryIndex, { global: { stubs } })
    expect(mockGetCategories).toHaveBeenCalled()
  })

  it('shows error message on load failure', async () => {
    mockGetCategories.mockRejectedValueOnce(new Error('fail'))
    mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载分类失败')
  })

  it('未填分类名称点保存提示警告', async () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '创建')
    await saveBtn!.trigger('click')
    expect(mockElMessage.warning).toHaveBeenCalledWith('请填写分类名称')
    expect(mockCreateCategory).not.toHaveBeenCalled()
  })

  it('填写名称后保存调用 createCategory', async () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const labelInput = inputs.find((c) => (c.props('placeholder') || '').includes('请输入分类名称'))
    await labelInput!.vm.$emit('update:modelValue', '新分类')
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '创建')
    await saveBtn!.trigger('click')
    await flushPromises()
    expect(mockCreateCategory).toHaveBeenCalledWith({
      label: '新分类',
      parent_id: null,
      description: '',
    })
    expect(mockElMessage.success).toHaveBeenCalledWith('分类已创建')
  })

  it('点击树节点后保存调用 updateCategory', async () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    const tree = wrapper.findComponent({ name: 'ElTree' })
    await tree.vm.$emit('node-click', {
      id: 5,
      label: '售后',
      parentId: 1,
      description: '售后相关',
      derived: false,
    })
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '保存修改')
    await saveBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateCategory).toHaveBeenCalledWith(5, {
      label: '售后',
      parent_id: 1,
      description: '售后相关',
    })
    expect(mockElMessage.success).toHaveBeenCalledWith('分类已更新')
  })

  it('选择分类后删除调用 deleteCategory', async () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    const tree = wrapper.findComponent({ name: 'ElTree' })
    await tree.vm.$emit('node-click', {
      id: 5,
      label: '售后',
      parentId: 1,
      description: 'd',
      derived: false,
    })
    await flushPromises()
    const delBtn = wrapper.findAll('button').find((b) => b.text() === '删除')
    await delBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessageBox.confirm).toHaveBeenCalled()
    expect(mockDeleteCategory).toHaveBeenCalledWith(5)
    expect(mockElMessage.success).toHaveBeenCalledWith('分类已删除')
  })

  it('点击新增分类按钮重置表单', async () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    const tree = wrapper.findComponent({ name: 'ElTree' })
    await tree.vm.$emit('node-click', {
      id: 5,
      label: '售后',
      parentId: 1,
      description: 'd',
      derived: false,
    })
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text() === '新增分类')
    await addBtn!.trigger('click')
    expect(wrapper.text()).toContain('新增分类')
  })

  it('删除确认取消时不调用 deleteCategory', async () => {
    mockElMessageBox.confirm.mockRejectedValueOnce(new Error('cancel'))
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    const tree = wrapper.findComponent({ name: 'ElTree' })
    await tree.vm.$emit('node-click', {
      id: 5,
      label: '售后',
      parentId: 1,
      description: 'd',
      derived: false,
    })
    await flushPromises()
    mockDeleteCategory.mockClear()
    const delBtn = wrapper.findAll('button').find((b) => b.text() === '删除')
    await delBtn!.trigger('click')
    await flushPromises()
    expect(mockDeleteCategory).not.toHaveBeenCalled()
  })

  it('deleteCategory 失败提示错误', async () => {
    mockDeleteCategory.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    const tree = wrapper.findComponent({ name: 'ElTree' })
    await tree.vm.$emit('node-click', {
      id: 5,
      label: '售后',
      parentId: 1,
      description: 'd',
      derived: false,
    })
    await flushPromises()
    const delBtn = wrapper.findAll('button').find((b) => b.text() === '删除')
    await delBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalled()
  })

  it('createCategory 失败提示错误', async () => {
    mockCreateCategory.mockRejectedValueOnce(new Error('fail'))
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const labelInput = inputs.find((c) => (c.props('placeholder') || '').includes('请输入分类名称'))
    await labelInput!.vm.$emit('update:modelValue', '新分类')
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '创建')
    await saveBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalled()
  })

  it('填写完整表单含描述和上级分类后保存', async () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    const labelInput = inputs.find((c) => (c.props('placeholder') || '').includes('请输入分类名称'))
    const descInput = inputs.find((c) => (c.props('placeholder') || '').includes('请输入分类描述'))
    await labelInput!.vm.$emit('update:modelValue', '二级分类')
    await descInput!.vm.$emit('update:modelValue', '描述内容')
    const treeSelect = wrapper.findComponent({ name: 'ElTreeSelect' })
    await treeSelect.vm.$emit('update:modelValue', 1)
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '创建')
    await saveBtn!.trigger('click')
    await flushPromises()
    expect(mockCreateCategory).toHaveBeenCalledWith({
      label: '二级分类',
      parent_id: 1,
      description: '描述内容',
    })
  })

  it('仅输入搜索关键词未填名称保存提示警告', async () => {
    const wrapper = mount(CategoryIndex, { global: { stubs } })
    await flushPromises()
    const searchInput = wrapper
      .findAllComponents({ name: 'ElInput' })
      .find((c) => (c.props('placeholder') || '').includes('搜索分类'))
    await searchInput!.vm.$emit('update:modelValue', '售后')
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '创建')
    await saveBtn!.trigger('click')
    expect(mockElMessage.warning).toHaveBeenCalledWith('请填写分类名称')
  })
})
