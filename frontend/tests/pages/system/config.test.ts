import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const { mockElMessage, mockGetConfig, mockSetConfig, mockReloadConfig } = vi.hoisted(() => ({
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockGetConfig: vi.fn(),
  mockSetConfig: vi.fn(),
  mockReloadConfig: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useRoute: () => ({ path: '/' }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: { confirm: vi.fn(() => Promise.resolve()), alert: vi.fn(() => Promise.resolve()) },
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => {
  const s = (n: string) => defineComponent({ name: n, render: () => h('span') })
  return {
    Setting: s('Setting'),
    Refresh: s('Refresh'),
    Edit: s('Edit'),
    Document: s('Document'),
    Key: s('Key'),
    Warning: s('Warning'),
    Shop: s('Shop'),
  }
})

vi.mock('@/api/system', () => ({
  getConfig: mockGetConfig,
  setConfig: mockSetConfig,
  reloadConfig: mockReloadConfig,
}))

import Config from '@/pages/system/config.vue'

const configData: Record<string, { key: string; value: any }> = {
  qa_statuses: { key: 'qa_statuses', value: ['待处理', '处理中', '已完成'] },
  brand_keywords: { key: 'brand_keywords', value: ['品牌A', '品牌B'] },
  forbidden_new_kws: { key: 'forbidden_new_kws', value: ['违规词'] },
  enterprise_name: { key: 'enterprise_name', value: '测试企业' },
}

describe('Config', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetConfig.mockImplementation((key: string) => Promise.resolve(configData[key]))
    mockReloadConfig.mockResolvedValue({})
  })

  const mountConfig = () => mount(Config, { global: { stubs: { ...commonStubs, ...iconStubs } } })

  it('渲染业务配置管理标题', async () => {
    const wrapper = mountConfig()
    await flushPromises()
    expect(wrapper.text()).toContain('业务配置管理')
  })

  it('渲染刷新缓存按钮', async () => {
    const wrapper = mountConfig()
    await flushPromises()
    expect(wrapper.text()).toContain('刷新缓存')
  })

  it('渲染说明副标题', async () => {
    const wrapper = mountConfig()
    await flushPromises()
    expect(wrapper.text()).toContain('管理系统运行参数')
  })

  it('初始挂载调用getConfig加载4个配置项', async () => {
    mountConfig()
    await flushPromises()
    expect(mockGetConfig).toHaveBeenCalledTimes(4)
  })

  it('配置卡片渲染正确数量与标题', async () => {
    const wrapper = mountConfig()
    await flushPromises()
    const cards = wrapper.findAll('.config-card')
    expect(cards.length).toBe(4)
    const text = wrapper.text()
    expect(text).toContain('工单状态列表')
    expect(text).toContain('品牌关键词')
    expect(text).toContain('禁用关键词')
    expect(text).toContain('企业名称')
  })

  it('点击编辑弹出编辑配置对话框', async () => {
    const wrapper = mountConfig()
    await flushPromises()
    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('编辑'))
    expect(editBtns.length).toBe(4)
    await editBtns[0].trigger('click')
    await flushPromises()
    const dialog = wrapper.findComponent({ name: 'ElDialog' })
    expect(dialog.props('title')).toBe('编辑配置')
  })

  it('对话框含保存与取消按钮', async () => {
    const wrapper = mountConfig()
    await flushPromises()
    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('编辑'))
    await editBtns[0].trigger('click')
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('保存')
    expect(text).toContain('取消')
  })

  it('点击刷新缓存调用reloadConfig', async () => {
    const wrapper = mountConfig()
    await flushPromises()
    const reloadBtn = wrapper.findAll('button').find((b) => b.text().includes('刷新缓存'))
    await reloadBtn!.trigger('click')
    await flushPromises()
    expect(mockReloadConfig).toHaveBeenCalled()
  })

  it('刷新缓存成功提示', async () => {
    mockReloadConfig.mockResolvedValue({})
    const wrapper = mountConfig()
    await flushPromises()
    const reloadBtn = wrapper.findAll('button').find((b) => b.text().includes('刷新缓存'))
    await reloadBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.success).toHaveBeenCalledWith('缓存已刷新')
  })

  it('刷新缓存失败提示错误', async () => {
    mockReloadConfig.mockRejectedValue(new Error('fail'))
    const wrapper = mountConfig()
    await flushPromises()
    const reloadBtn = wrapper.findAll('button').find((b) => b.text().includes('刷新缓存'))
    await reloadBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('刷新失败')
  })

  it('保存配置调用setConfig并提示成功', async () => {
    mockSetConfig.mockResolvedValue({})
    const wrapper = mountConfig()
    await flushPromises()
    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('编辑'))
    await editBtns[0].trigger('click')
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '保存')
    await saveBtn!.trigger('click')
    await flushPromises()
    expect(mockSetConfig).toHaveBeenCalledWith('qa_statuses', expect.any(Array))
    expect(mockElMessage.success).toHaveBeenCalledWith('保存成功')
  })

  it('保存配置失败提示错误', async () => {
    mockSetConfig.mockRejectedValue(new Error('fail'))
    const wrapper = mountConfig()
    await flushPromises()
    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('编辑'))
    await editBtns[0].trigger('click')
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '保存')
    await saveBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('保存失败，请检查格式')
  })

  it('加载配置部分失败仍渲染已成功项', async () => {
    mockGetConfig.mockImplementation((key: string) => {
      if (key === 'brand_keywords') return Promise.reject(new Error('fail'))
      return Promise.resolve(configData[key])
    })
    const wrapper = mountConfig()
    await flushPromises()
    const cards = wrapper.findAll('.config-card')
    expect(cards.length).toBe(3)
  })

  it('保存字符串配置调用setConfig', async () => {
    mockSetConfig.mockResolvedValue({})
    const wrapper = mountConfig()
    await flushPromises()
    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('编辑'))
    await editBtns[3].trigger('click')
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '保存')
    await saveBtn!.trigger('click')
    await flushPromises()
    expect(mockSetConfig).toHaveBeenCalledWith('enterprise_name', '测试企业')
    expect(mockElMessage.success).toHaveBeenCalledWith('保存成功')
  })

  it('覆盖所有v-model与取消按钮事件处理', async () => {
    const wrapper = mountConfig()
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    inputs.forEach((i) => i.vm.$emit('update:modelValue', 'x'))
    const dialogs = wrapper.findAllComponents({ name: 'ElDialog' })
    dialogs.forEach((d) => {
      d.vm.$emit('update:modelValue', true)
      d.vm.$emit('update:modelValue', false)
    })
    await flushPromises()
    const editBtns = wrapper.findAll('button').filter((b) => b.text().includes('编辑'))
    await editBtns[0].trigger('click')
    await flushPromises()
    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === '取消')
    if (cancelBtn) await cancelBtn.trigger('click')
    await flushPromises()
  })
})
