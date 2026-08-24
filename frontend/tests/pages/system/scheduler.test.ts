import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockElMessage,
  mockElMessageBox,
  mockGetSchedulerStatus,
  mockTriggerSchedulerJob,
  mockUpdateSchedulerConfig,
  mockGetSchedulerLogs,
} = vi.hoisted(() => ({
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(() => Promise.resolve()),
  },
  mockGetSchedulerStatus: vi.fn(),
  mockTriggerSchedulerJob: vi.fn(),
  mockUpdateSchedulerConfig: vi.fn(),
  mockGetSchedulerLogs: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
  useRoute: () => ({ path: '/' }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
  ElMessageBox: mockElMessageBox,
  ElNotification: vi.fn(),
}))

vi.mock('@element-plus/icons-vue', () => {
  const s = (n: string) => defineComponent({ name: n, render: () => h('span') })
  return {
    VideoPlay: s('VideoPlay'),
    VideoPause: s('VideoPause'),
    Refresh: s('Refresh'),
    Setting: s('Setting'),
    Clock: s('Clock'),
    Edit: s('Edit'),
    Lightning: s('Lightning'),
  }
})

vi.mock('@/api/system', () => ({
  getSchedulerStatus: mockGetSchedulerStatus,
  triggerSchedulerJob: mockTriggerSchedulerJob,
  updateSchedulerConfig: mockUpdateSchedulerConfig,
  getSchedulerLogs: mockGetSchedulerLogs,
}))

import Scheduler from '@/pages/system/scheduler.vue'

const schedulerStatus = {
  running: true,
  jobs: [
    { id: 'sync_and_ingest', next_run_time: '2024-12-31 00:00:00', trigger: 'interval' },
    { id: 'cleanup', next_run_time: '2024-12-31 01:00:00', trigger: 'interval' },
    { id: 'alert_check', next_run_time: null, trigger: 'interval' },
  ],
  task_stats: {
    sync_and_ingest: { success: 90, fail: 10, total: 100, success_rate: 90 },
    cleanup: { success: 50, fail: 0, total: 50, success_rate: 100 },
  },
}

const schedulerLogs = {
  items: [
    {
      id: 1,
      task_name: 'sync_and_ingest',
      stats: '{"success":90,"fail":10}',
      result: 'success',
      created_at: '2024-01-01 00:00:00',
    },
    {
      id: 2,
      task_name: 'cleanup',
      stats: '{"success":50,"fail":0}',
      result: 'success',
      created_at: '2024-01-02 00:00:00',
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
}

describe('Scheduler', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetSchedulerStatus.mockResolvedValue(schedulerStatus)
    mockGetSchedulerLogs.mockResolvedValue(schedulerLogs)
  })

  const tableColStub = {
    name: 'ElTableColumn',
    props: ['type', 'width', 'prop', 'label', 'fixed', 'align', 'minWidth', 'showOverflowTooltip'],
    template: '<div class="el-table-col-stub"></div>',
  }
  const mountScheduler = () =>
    mount(Scheduler, {
      global: { stubs: { ...commonStubs, ...iconStubs, ElTableColumn: tableColStub } },
    })

  it('渲染调度器运行中状态', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    expect(wrapper.text()).toContain('调度器运行中')
    wrapper.unmount()
  })

  it('渲染刷新按钮', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    expect(wrapper.text()).toContain('刷新')
    wrapper.unmount()
  })

  it('渲染执行日志标题', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    expect(wrapper.text()).toContain('执行日志')
    wrapper.unmount()
  })

  it('渲染执行日志表格与分页', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    expect(wrapper.find('.el-table-stub').exists()).toBe(true)
    expect(wrapper.find('.el-pagination-stub').exists()).toBe(true)
    wrapper.unmount()
  })

  it('初始挂载调用getSchedulerStatus与getSchedulerLogs', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    expect(mockGetSchedulerStatus).toHaveBeenCalled()
    expect(mockGetSchedulerLogs).toHaveBeenCalled()
    wrapper.unmount()
  })

  it('任务卡片渲染正确数量与操作按钮', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    const cards = wrapper.findAll('.task-card')
    expect(cards.length).toBe(3)
    const text = wrapper.text()
    expect(text).toContain('手动触发')
    expect(text).toContain('修改调度')
    wrapper.unmount()
  })

  it('点击修改调度弹出对话框', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text().includes('修改调度'))
    await editBtn!.trigger('click')
    await flushPromises()
    const dialog = wrapper.findComponent({ name: 'ElDialog' })
    expect(dialog.props('title')).toBe('修改调度时间')
    wrapper.unmount()
  })

  it('渲染任务中文名称', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('工单同步入库')
    expect(text).toContain('过期数据清理')
    expect(text).toContain('告警规则检查')
    wrapper.unmount()
  })

  it('点击手动触发调用confirm后调用triggerSchedulerJob', async () => {
    mockTriggerSchedulerJob.mockResolvedValue({})
    const wrapper = mountScheduler()
    await flushPromises()
    const triggerBtn = wrapper.findAll('button').find((b) => b.text().includes('手动触发'))
    await triggerBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessageBox.confirm).toHaveBeenCalled()
    expect(mockTriggerSchedulerJob).toHaveBeenCalledWith('sync_and_ingest')
    expect(mockElMessage.success).toHaveBeenCalledWith('任务已触发')
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('手动触发失败提示错误', async () => {
    mockTriggerSchedulerJob.mockRejectedValue(new Error('fail'))
    const wrapper = mountScheduler()
    await flushPromises()
    const triggerBtn = wrapper.findAll('button').find((b) => b.text().includes('手动触发'))
    await triggerBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('触发失败')
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('保存调度调用updateSchedulerConfig并提示成功', async () => {
    mockUpdateSchedulerConfig.mockResolvedValue({})
    const wrapper = mountScheduler()
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text().includes('修改调度'))
    await editBtn!.trigger('click')
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '保存')
    await saveBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateSchedulerConfig).toHaveBeenCalledWith('sync_and_ingest', 1, undefined)
    expect(mockElMessage.success).toHaveBeenCalledWith('调度时间已更新')
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('更新调度失败提示错误', async () => {
    mockUpdateSchedulerConfig.mockRejectedValue(new Error('fail'))
    const wrapper = mountScheduler()
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text().includes('修改调度'))
    await editBtn!.trigger('click')
    await flushPromises()
    const saveBtn = wrapper.findAll('button').find((b) => b.text() === '保存')
    await saveBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('更新失败')
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('点击顶部刷新调用getSchedulerStatus', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    mockGetSchedulerStatus.mockClear()
    const refreshBtn = wrapper
      .find('.status-banner')
      .findAll('button')
      .find((b) => b.text().includes('刷新'))
    await refreshBtn!.trigger('click')
    await flushPromises()
    expect(mockGetSchedulerStatus).toHaveBeenCalled()
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('点击执行日志刷新调用getSchedulerLogs', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    mockGetSchedulerLogs.mockClear()
    const refreshBtns = wrapper.findAll('button').filter((b) => b.text().includes('刷新'))
    await refreshBtns[refreshBtns.length - 1].trigger('click')
    await flushPromises()
    expect(mockGetSchedulerLogs).toHaveBeenCalled()
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('加载调度器状态失败提示错误', async () => {
    mockGetSchedulerStatus.mockRejectedValue(new Error('fail'))
    const wrapper = mountScheduler()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载调度器状态失败')
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('加载调度日志失败提示错误', async () => {
    mockGetSchedulerLogs.mockRejectedValue(new Error('fail'))
    const wrapper = mountScheduler()
    await flushPromises()
    mockGetSchedulerLogs.mockClear()
    mockGetSchedulerLogs.mockRejectedValue(new Error('fail'))
    const refreshBtns = wrapper.findAll('button').filter((b) => b.text().includes('刷新'))
    await refreshBtns[refreshBtns.length - 1].trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载日志失败')
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('分页current-change触发日志重新加载', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    mockGetSchedulerLogs.mockClear()
    wrapper.findComponent({ name: 'ElPagination' }).vm.$emit('current-change', 2)
    await flushPromises()
    expect(mockGetSchedulerLogs).toHaveBeenCalled()
    vi.clearAllTimers()
    wrapper.unmount()
  })

  it('覆盖所有v-model与取消按钮事件处理', async () => {
    const wrapper = mountScheduler()
    await flushPromises()
    const selects = wrapper.findAllComponents({ name: 'ElSelect' })
    selects.forEach((s) => s.vm.$emit('update:modelValue', 'minutes'))
    const dialogs = wrapper.findAllComponents({ name: 'ElDialog' })
    dialogs.forEach((d) => {
      d.vm.$emit('update:modelValue', true)
      d.vm.$emit('update:modelValue', false)
    })
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    pagination.vm.$emit('update:currentPage', 2)
    pagination.vm.$emit('update:pageSize', 20)
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text().includes('修改调度'))
    await editBtn!.trigger('click')
    await flushPromises()
    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === '取消')
    if (cancelBtn) await cancelBtn.trigger('click')
    await flushPromises()
    vi.clearAllTimers()
    wrapper.unmount()
  })
})
