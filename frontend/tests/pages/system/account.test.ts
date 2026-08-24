import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockElMessage,
  mockElMessageBox,
  mockGetUserList,
  mockCreateUser,
  mockUpdateUser,
  mockResetPassword,
  mockDeleteUser,
  mockGetRoleList,
} = vi.hoisted(() => ({
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(() => Promise.resolve()),
  },
  mockGetUserList: vi.fn(),
  mockCreateUser: vi.fn(),
  mockUpdateUser: vi.fn(),
  mockResetPassword: vi.fn(),
  mockDeleteUser: vi.fn(),
  mockGetRoleList: vi.fn(),
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
    UserFilled: s('UserFilled'),
    CircleCheck: s('CircleCheck'),
    CircleClose: s('CircleClose'),
    Avatar: s('Avatar'),
    Plus: s('Plus'),
  }
})

vi.mock('@/api/system', () => ({
  getUserList: mockGetUserList,
  createUser: mockCreateUser,
  updateUser: mockUpdateUser,
  resetPassword: mockResetPassword,
  deleteUser: mockDeleteUser,
  getRoleList: mockGetRoleList,
}))

vi.mock('@/utils/roleColor', () => ({
  roleColor: vi.fn(() => '#1677FF'),
}))

import Account from '@/pages/system/account.vue'

const roleList = [
  { id: 1, role_key: 'superadmin', role_name: '超级管理员', description: '', permissions: [] },
  { id: 2, role_key: 'admin', role_name: '业务管理员', description: '', permissions: [] },
  { id: 3, role_key: 'ops', role_name: '运维工程师', description: '', permissions: [] },
]

const userList = {
  items: [
    {
      id: 1,
      username: 'superadmin',
      role: 'superadmin',
      dept: '',
      status: 'active',
      created_at: '2024-01-01 00:00:00',
    },
    {
      id: 2,
      username: 'admin',
      role: 'admin',
      dept: 'aftersale',
      status: 'active',
      created_at: '2024-01-02 00:00:00',
    },
    {
      id: 3,
      username: 'ops',
      role: 'ops',
      dept: '',
      status: 'disabled',
      created_at: '2024-01-03 00:00:00',
    },
  ],
  total: 3,
  page: 1,
  page_size: 10,
}

describe('Account', () => {
  let mockRow: any = {
    id: 2,
    username: 'admin',
    role: 'admin',
    dept: 'aftersale',
    status: 'active',
    created_at: '2024-01-02 00:00:00',
  }

  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetRoleList.mockResolvedValue(roleList)
    mockGetUserList.mockResolvedValue(userList)
    mockRow = {
      id: 2,
      username: 'admin',
      role: 'admin',
      dept: 'aftersale',
      status: 'active',
      created_at: '2024-01-02 00:00:00',
    }
  })

  const tableColStub = {
    name: 'ElTableColumn',
    props: ['type', 'width', 'prop', 'label', 'fixed', 'align', 'minWidth', 'showOverflowTooltip'],
    data: () => ({ row: mockRow }),
    template: '<div class="el-table-col-stub"><slot :row="row" /></div>',
  }
  const elInputStub = {
    name: 'ElInput',
    props: ['modelValue', 'placeholder', 'type', 'clearable', 'disabled', 'size'],
    emits: ['update:modelValue', 'change', 'blur', 'focus'],
    template:
      '<input :value="modelValue" :placeholder="placeholder" :disabled="disabled" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  }
  const elSelectStub = {
    name: 'ElSelect',
    props: ['modelValue', 'placeholder', 'clearable', 'disabled', 'size'],
    emits: ['update:modelValue', 'change'],
    template:
      '<select class="el-select-stub" :value="modelValue" :placeholder="placeholder" @change="$emit(\'update:modelValue\', $event.target.value)"><slot></slot></select>',
  }
  const mountAccount = () =>
    mount(Account, {
      global: {
        stubs: {
          ...commonStubs,
          ...iconStubs,
          ElTableColumn: tableColStub,
          ElInput: elInputStub,
          ElSelect: elSelectStub,
        },
      },
    })

  it('渲染账号管理标题', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    expect(wrapper.text()).toContain('账号管理')
  })

  it('渲染4个KPI概览标签', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('总账号数')
    expect(text).toContain('启用')
    expect(text).toContain('禁用')
    expect(text).toContain('超管数')
  })

  it('渲染新增账号按钮', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    expect(wrapper.text()).toContain('新增账号')
  })

  it('渲染筛选区与搜索重置按钮', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    expect(wrapper.findAll('.el-select-stub').length).toBeGreaterThanOrEqual(2)
    const text = wrapper.text()
    expect(text).toContain('搜索')
    expect(text).toContain('重置')
  })

  it('渲染表格与分页组件', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    expect(wrapper.find('.el-table-stub').exists()).toBe(true)
    expect(wrapper.find('.el-pagination-stub').exists()).toBe(true)
  })

  it('初始挂载调用getUserList与getRoleList', async () => {
    mountAccount()
    await flushPromises()
    expect(mockGetUserList).toHaveBeenCalled()
    expect(mockGetRoleList).toHaveBeenCalled()
  })

  it('KPI数字正确反映列表数据', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    const nums = wrapper.findAll('.kpi-num')
    expect(nums[0].text()).toBe('3')
    expect(nums[1].text()).toBe('2')
    expect(nums[2].text()).toBe('1')
    expect(nums[3].text()).toBe('1')
  })

  it('点击新增账号弹出对话框含表单项', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    const buttons = wrapper.findAll('button')
    const addBtn = buttons.find((b) => b.text().includes('新增账号'))
    await addBtn!.trigger('click')
    await flushPromises()
    const dialogs = wrapper.findAllComponents({ name: 'ElDialog' })
    expect(dialogs.length).toBeGreaterThanOrEqual(1)
    expect(dialogs[0].props('title')).toBe('新增账号')
    expect(wrapper.findAll('.el-form-item-stub').length).toBeGreaterThanOrEqual(1)
  })

  it('点击编辑按钮弹出编辑账号对话框', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text() === '编辑')
    await editBtn!.trigger('click')
    await flushPromises()
    const dialog = wrapper.findComponent({ name: 'ElDialog' })
    expect(dialog.props('title')).toBe('编辑账号')
  })

  it('提交新增账号调用createUser并提示成功', async () => {
    mockCreateUser.mockResolvedValue({})
    const wrapper = mountAccount()
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增账号'))
    await addBtn!.trigger('click')
    await flushPromises()
    await wrapper.find('input[placeholder="请输入用户名"]').setValue('newuser')
    await wrapper.find('input[placeholder="请输入初始密码"]').setValue('pwd123')
    await wrapper.find('select[placeholder="请选择角色"]').setValue('admin')
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockCreateUser).toHaveBeenCalledWith(
      expect.objectContaining({ username: 'newuser', role: 'admin' })
    )
    expect(mockElMessage.success).toHaveBeenCalledWith('账号创建成功')
  })

  it('提交编辑账号调用updateUser并提示成功', async () => {
    mockUpdateUser.mockResolvedValue({})
    const wrapper = mountAccount()
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text() === '编辑')
    await editBtn!.trigger('click')
    await flushPromises()
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateUser).toHaveBeenCalledWith(2, expect.any(Object))
    expect(mockElMessage.success).toHaveBeenCalledWith('账号已更新')
  })

  it('点击删除调用confirm后调用deleteUser', async () => {
    mockDeleteUser.mockResolvedValue({})
    mockRow = {
      id: 3,
      username: 'ops',
      role: 'ops',
      dept: '',
      status: 'disabled',
      created_at: '2024-01-03 00:00:00',
    }
    const wrapper = mountAccount()
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find((b) => b.text() === '删除')
    await deleteBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessageBox.confirm).toHaveBeenCalled()
    expect(mockDeleteUser).toHaveBeenCalledWith(3)
    expect(mockElMessage.success).toHaveBeenCalledWith('已删除')
  })

  it('重置密码调用resetPassword并提示成功', async () => {
    mockResetPassword.mockResolvedValue({})
    const wrapper = mountAccount()
    await flushPromises()
    const resetBtn = wrapper.findAll('button').find((b) => b.text() === '重置密码')
    await resetBtn!.trigger('click')
    await flushPromises()
    const dialogs = wrapper.findAllComponents({ name: 'ElDialog' })
    const resetDialog = dialogs.find((d) => d.props('title') === '重置密码')
    expect(resetDialog).toBeDefined()
    await wrapper.find('input[placeholder="请输入新密码"]').setValue('newpwd123')
    const confirmResetBtn = wrapper.findAll('button').find((b) => b.text() === '确认重置')
    await confirmResetBtn!.trigger('click')
    await flushPromises()
    expect(mockResetPassword).toHaveBeenCalledWith(2, 'newpwd123')
    expect(mockElMessage.success).toHaveBeenCalledWith('密码已重置')
  })

  it('点击禁用按钮调用updateUser切换状态', async () => {
    mockUpdateUser.mockResolvedValue({})
    const wrapper = mountAccount()
    await flushPromises()
    const disableBtn = wrapper.findAll('button').find((b) => b.text() === '禁用')
    await disableBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateUser).toHaveBeenCalledWith(2, { status: 'disabled' })
    expect(mockElMessage.success).toHaveBeenCalledWith('已禁用')
  })

  it('点击启用按钮调用updateUser启用账号', async () => {
    mockUpdateUser.mockResolvedValue({})
    mockRow = {
      id: 3,
      username: 'ops',
      role: 'ops',
      dept: '',
      status: 'disabled',
      created_at: '2024-01-03 00:00:00',
    }
    const wrapper = mountAccount()
    await flushPromises()
    const enableBtn = wrapper.findAll('button').find((b) => b.text() === '启用')
    await enableBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateUser).toHaveBeenCalledWith(3, { status: 'active' })
    expect(mockElMessage.success).toHaveBeenCalledWith('已启用')
  })

  it('点击搜索调用getUserList重新加载', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    mockGetUserList.mockClear()
    const searchBtn = wrapper.findAll('button').find((b) => b.text() === '搜索')
    await searchBtn!.trigger('click')
    await flushPromises()
    expect(mockGetUserList).toHaveBeenCalled()
  })

  it('点击重置清空筛选并重新加载', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    mockGetUserList.mockClear()
    const resetBtn = wrapper.findAll('button').find((b) => b.text() === '重置')
    await resetBtn!.trigger('click')
    await flushPromises()
    expect(mockGetUserList).toHaveBeenCalled()
  })

  it('加载账号列表失败提示错误', async () => {
    mockGetUserList.mockRejectedValue(new Error('fail'))
    const wrapper = mountAccount()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载账号列表失败')
  })

  it('提交新增账号缺少角色提示警告', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增账号'))
    await addBtn!.trigger('click')
    await flushPromises()
    await wrapper.find('input[placeholder="请输入用户名"]').setValue('newuser')
    await wrapper.find('input[placeholder="请输入初始密码"]').setValue('pwd123')
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.warning).toHaveBeenCalledWith('用户名和角色不能为空')
  })

  it('提交新增账号失败提示错误', async () => {
    mockCreateUser.mockRejectedValue(new Error('fail'))
    const wrapper = mountAccount()
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增账号'))
    await addBtn!.trigger('click')
    await flushPromises()
    await wrapper.find('input[placeholder="请输入用户名"]').setValue('newuser')
    await wrapper.find('input[placeholder="请输入初始密码"]').setValue('pwd123')
    await wrapper.find('select[placeholder="请选择角色"]').setValue('admin')
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('创建失败，用户名可能已存在')
  })

  it('提交编辑账号失败提示错误', async () => {
    mockUpdateUser.mockRejectedValue(new Error('fail'))
    const wrapper = mountAccount()
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text() === '编辑')
    await editBtn!.trigger('click')
    await flushPromises()
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('更新失败')
  })

  it('删除账号失败提示错误', async () => {
    mockDeleteUser.mockRejectedValue(new Error('fail'))
    const wrapper = mountAccount()
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find((b) => b.text() === '删除')
    await deleteBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('删除失败')
  })

  it('重置密码失败提示错误', async () => {
    mockResetPassword.mockRejectedValue(new Error('fail'))
    const wrapper = mountAccount()
    await flushPromises()
    const resetBtn = wrapper.findAll('button').find((b) => b.text() === '重置密码')
    await resetBtn!.trigger('click')
    await flushPromises()
    await wrapper.find('input[placeholder="请输入新密码"]').setValue('newpwd123')
    const confirmResetBtn = wrapper.findAll('button').find((b) => b.text() === '确认重置')
    await confirmResetBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('重置失败')
  })

  it('切换状态失败提示错误', async () => {
    mockUpdateUser.mockRejectedValue(new Error('fail'))
    const wrapper = mountAccount()
    await flushPromises()
    const disableBtn = wrapper.findAll('button').find((b) => b.text() === '禁用')
    await disableBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('操作失败')
  })

  it('覆盖所有v-model与取消按钮事件处理', async () => {
    const wrapper = mountAccount()
    await flushPromises()
    const selects = wrapper.findAllComponents({ name: 'ElSelect' })
    selects.forEach((s) => s.vm.$emit('update:modelValue', 'x'))
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    inputs.forEach((i) => i.vm.$emit('update:modelValue', 'x'))
    const pagination = wrapper.findComponent({ name: 'ElPagination' })
    pagination.vm.$emit('update:currentPage', 2)
    pagination.vm.$emit('update:pageSize', 20)
    const dialogs = wrapper.findAllComponents({ name: 'ElDialog' })
    dialogs.forEach((d) => {
      d.vm.$emit('update:modelValue', true)
      d.vm.$emit('close')
    })
    await flushPromises()
    const cancelBtns = wrapper.findAll('button').filter((b) => b.text() === '取消')
    for (const b of cancelBtns) {
      await b.trigger('click')
    }
    await flushPromises()
  })
})
