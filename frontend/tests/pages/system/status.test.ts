import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const { mockElMessage, mockGetSystemStatus, mockGetSystemLogs } = vi.hoisted(() => ({
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockGetSystemStatus: vi.fn(),
  mockGetSystemLogs: vi.fn(),
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
    CircleCheck: s('CircleCheck'),
    CircleClose: s('CircleClose'),
    Warning: s('Warning'),
    Refresh: s('Refresh'),
    Link: s('Link'),
    Document: s('Document'),
    Cpu: s('Cpu'),
    Coin: s('Coin'),
    Box: s('Box'),
    Microphone: s('Microphone'),
    Timer: s('Timer'),
    Bell: s('Bell'),
    Monitor: s('Monitor'),
    Stopwatch: s('Stopwatch'),
  }
})

vi.mock('@/api/system', () => ({
  getSystemStatus: mockGetSystemStatus,
  getSystemLogs: mockGetSystemLogs,
}))

import Status from '@/pages/system/status.vue'

const systemStatus = {
  overall: 'healthy',
  components: [
    { name: 'API服务', status: 'healthy', latency_ms: 50, detail: '运行正常' },
    { name: 'MySQL', status: 'healthy', latency_ms: 10, detail: '连接正常' },
    { name: 'Milvus', status: 'degraded', latency_ms: 200, detail: '响应缓慢' },
    { name: 'ASR', status: 'standby', latency_ms: 0, detail: '待加载' },
  ],
  timestamp: '2024-01-01 12:00:00',
}

const systemLogs = {
  logs: [
    { line: 'Server started', level: 'INFO' },
    { line: 'Database error', level: 'ERROR' },
    { line: 'High memory', level: 'WARNING' },
  ],
  total: 3,
}

describe('Status', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetSystemStatus.mockResolvedValue(systemStatus)
    mockGetSystemLogs.mockResolvedValue(systemLogs)
    vi.stubGlobal('open', vi.fn())
  })

  const mountStatus = () => mount(Status, { global: { stubs: { ...commonStubs, ...iconStubs } } })

  it('渲染系统运行正常标题', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    expect(wrapper.text()).toContain('系统运行正常')
    wrapper.unmount()
  })

  it('渲染刷新与LangSmith按钮', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('刷新')
    expect(text).toContain('LangSmith')
    wrapper.unmount()
  })

  it('渲染系统日志标题', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    expect(wrapper.text()).toContain('系统日志')
    wrapper.unmount()
  })

  it('渲染组件状态卡片', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    const cards = wrapper.findAll('.comp-card')
    expect(cards.length).toBe(4)
    wrapper.unmount()
  })

  it('初始挂载调用getSystemStatus与getSystemLogs', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    expect(mockGetSystemStatus).toHaveBeenCalled()
    expect(mockGetSystemLogs).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('健康计数正确反映组件状态', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    expect(wrapper.find('.hc-num').text()).toBe('2')
    expect(wrapper.text()).toContain('/ 4 正常')
    wrapper.unmount()
  })

  it('渲染终端日志区域', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    expect(wrapper.find('.terminal').exists()).toBe(true)
    wrapper.unmount()
  })

  it('渲染组件名称与状态文本', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('API服务')
    expect(text).toContain('MySQL')
    expect(text).toContain('正常')
    expect(text).toContain('降级')
    wrapper.unmount()
  })

  it('点击刷新调用getSystemStatus', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    mockGetSystemStatus.mockClear()
    const refreshBtn = wrapper.findAll('button').find((b) => b.text().includes('刷新'))
    await refreshBtn!.trigger('click')
    await flushPromises()
    expect(mockGetSystemStatus).toHaveBeenCalled()
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('点击LangSmith调用window.open', async () => {
    const mockOpen = vi.fn()
    vi.stubGlobal('open', mockOpen)
    const wrapper = mountStatus()
    await flushPromises()
    const langsmithBtn = wrapper.findAll('button').find((b) => b.text().includes('LangSmith'))
    await langsmithBtn!.trigger('click')
    await flushPromises()
    expect(mockOpen).toHaveBeenCalledWith('https://smith.langchain.com', '_blank')
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('切换日志级别调用getSystemLogs', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    mockGetSystemLogs.mockClear()
    wrapper.findComponent({ name: 'ElSelect' }).vm.$emit('change', 'WARNING')
    await flushPromises()
    expect(mockGetSystemLogs).toHaveBeenCalled()
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('点击日志刷新按钮调用getSystemLogs', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    mockGetSystemLogs.mockClear()
    const refreshBtn = wrapper.find('.log-actions').findAll('button')[0]
    await refreshBtn.trigger('click')
    await flushPromises()
    expect(mockGetSystemLogs).toHaveBeenCalled()
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('加载系统状态失败提示错误', async () => {
    mockGetSystemStatus.mockRejectedValue(new Error('fail'))
    const wrapper = mountStatus()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载系统状态失败')
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('加载系统日志失败提示错误', async () => {
    mockGetSystemLogs.mockRejectedValue(new Error('fail'))
    const wrapper = mountStatus()
    await flushPromises()
    mockGetSystemLogs.mockClear()
    mockGetSystemLogs.mockRejectedValue(new Error('fail'))
    const refreshBtn = wrapper.find('.log-actions').findAll('button')[0]
    await refreshBtn.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载日志失败')
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('覆盖所有v-model事件处理', async () => {
    const wrapper = mountStatus()
    await flushPromises()
    const selects = wrapper.findAllComponents({ name: 'ElSelect' })
    selects.forEach((s) => s.vm.$emit('update:modelValue', 'INFO'))
    await flushPromises()
    vi.clearAllTimers()
    wrapper.unmount()
  })
})
