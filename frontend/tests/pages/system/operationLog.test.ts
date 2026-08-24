import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const { mockElMessage, mockGetOperationList } = vi.hoisted(() => ({
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockGetOperationList: vi.fn(),
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
    Document: s('Document'),
    CirclePlus: s('CirclePlus'),
    Edit: s('Edit'),
    Delete: s('Delete'),
    Refresh: s('Refresh'),
    Warning: s('Warning'),
  }
})

vi.mock('@/api/system', () => ({
  getOperationList: mockGetOperationList,
}))

import OperationLog from '@/pages/system/operationLog.vue'

const operationList = {
  items: [
    {
      id: 1,
      operator: 'superadmin',
      action: 'create',
      target_type: 'user',
      target_id: 2,
      detail: '创建用户admin',
      ip: '127.0.0.1',
      created_at: '2024-01-01 00:00:00',
    },
    {
      id: 2,
      operator: 'superadmin',
      action: 'update',
      target_type: 'user',
      target_id: 2,
      detail: '修改用户角色',
      ip: '127.0.0.1',
      created_at: '2024-01-02 00:00:00',
    },
    {
      id: 3,
      operator: 'ops',
      action: 'delete',
      target_type: 'role',
      target_id: 5,
      detail: '删除角色test',
      ip: '127.0.0.1',
      created_at: '2024-01-03 00:00:00',
    },
    {
      id: 4,
      operator: 'superadmin',
      action: 'reset_password',
      target_type: 'user',
      target_id: 3,
      detail: '重置ops密码',
      ip: '127.0.0.1',
      created_at: '2024-01-04 00:00:00',
    },
  ],
  total: 4,
  page: 1,
  page_size: 20,
}

describe('OperationLog', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetOperationList.mockResolvedValue(operationList)
  })

  const tableColStub = {
    name: 'ElTableColumn',
    props: ['type', 'width', 'prop', 'label', 'fixed', 'align', 'minWidth', 'showOverflowTooltip'],
    template: '<div class="el-table-col-stub"></div>',
  }
  const mountOpLog = () =>
    mount(OperationLog, {
      global: { stubs: { ...commonStubs, ...iconStubs, ElTableColumn: tableColStub } },
    })

  it('渲染操作日志标题', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    expect(wrapper.text()).toContain('操作日志')
  })

  it('渲染4个KPI标签', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('总操作数')
    expect(text).toContain('创建操作')
    expect(text).toContain('修改操作')
    expect(text).toContain('删除操作')
  })

  it('渲染表格与时间线切换按钮', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('表格')
    expect(text).toContain('时间线')
  })

  it('渲染搜索与重置按钮', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('搜索')
    expect(text).toContain('重置')
  })

  it('渲染表格与分页组件', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    expect(wrapper.find('.el-table-stub').exists()).toBe(true)
    expect(wrapper.find('.el-pagination-stub').exists()).toBe(true)
  })

  it('初始挂载调用getOperationList', async () => {
    mountOpLog()
    await flushPromises()
    expect(mockGetOperationList).toHaveBeenCalled()
  })

  it('KPI数字正确反映操作数据', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    const nums = wrapper.findAll('.kpi-num')
    expect(nums[0].text()).toBe('4')
    expect(nums[1].text()).toBe('1')
    expect(nums[2].text()).toBe('1')
    expect(nums[3].text()).toBe('1')
  })

  it('点击搜索调用getOperationList重新加载', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    mockGetOperationList.mockClear()
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索')
    await searchBtn!.trigger('click')
    await flushPromises()
    expect(mockGetOperationList).toHaveBeenCalled()
  })

  it('点击重置清空筛选并重新加载', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    mockGetOperationList.mockClear()
    const resetBtn = wrapper.findAll('button').find((b) => b.text() === '重置')
    await resetBtn!.trigger('click')
    await flushPromises()
    expect(mockGetOperationList).toHaveBeenCalled()
  })

  it('切换时间线视图渲染时间线', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    await wrapper.findComponent({ name: 'ElRadioGroup' }).setValue('timeline')
    await flushPromises()
    expect(wrapper.find('.timeline-view').exists()).toBe(true)
  })

  it('切换回表格视图渲染表格', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    await wrapper.findComponent({ name: 'ElRadioGroup' }).setValue('timeline')
    await flushPromises()
    await wrapper.findComponent({ name: 'ElRadioGroup' }).setValue('table')
    await flushPromises()
    expect(wrapper.find('.el-table-stub').exists()).toBe(true)
  })

  it('分页current-change触发重新加载', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    mockGetOperationList.mockClear()
    wrapper.findComponent({ name: 'ElPagination' }).vm.$emit('current-change', 2)
    await flushPromises()
    expect(mockGetOperationList).toHaveBeenCalled()
  })

  it('加载操作日志失败提示错误', async () => {
    mockGetOperationList.mockRejectedValue(new Error('fail'))
    const wrapper = mountOpLog()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载操作日志失败')
  })

  it('分页size-change触发重新加载', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    mockGetOperationList.mockClear()
    wrapper.findComponent({ name: 'ElPagination' }).vm.$emit('size-change', 50)
    await flushPromises()
    expect(mockGetOperationList).toHaveBeenCalled()
  })

  it('覆盖所有v-model事件处理', async () => {
    const wrapper = mountOpLog()
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    inputs.forEach((i) => i.vm.$emit('update:modelValue', 'x'))
    const selects = wrapper.findAllComponents({ name: 'ElSelect' })
    selects.forEach((s) => s.vm.$emit('update:modelValue', 'x'))
    const radio = wrapper.findComponent({ name: 'ElRadioGroup' })
    radio.vm.$emit('update:modelValue', 'timeline')
    radio.vm.$emit('update:modelValue', 'table')
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    pagination.vm.$emit('update:currentPage', 2)
    pagination.vm.$emit('update:pageSize', 20)
    await flushPromises()
  })
})
