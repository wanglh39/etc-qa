import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import { defineComponent, h } from 'vue'
import { commonStubs, iconStubs } from '../../helpers/stubs'

const {
  mockElMessage,
  mockElMessageBox,
  mockGetRoleList,
  mockCreateRole,
  mockUpdateRole,
  mockDeleteRole,
  mockGetUserList,
} = vi.hoisted(() => ({
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockElMessageBox: {
    confirm: vi.fn(() => Promise.resolve()),
    alert: vi.fn(() => Promise.resolve()),
  },
  mockGetRoleList: vi.fn(),
  mockCreateRole: vi.fn(),
  mockUpdateRole: vi.fn(),
  mockDeleteRole: vi.fn(),
  mockGetUserList: vi.fn(),
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
    Setting: s('Setting'),
    Monitor: s('Monitor'),
    Service: s('Service'),
    Ticket: s('Ticket'),
    User: s('User'),
    Plus: s('Plus'),
  }
})

vi.mock('@/api/system', () => ({
  getRoleList: mockGetRoleList,
  createRole: mockCreateRole,
  updateRole: mockUpdateRole,
  deleteRole: mockDeleteRole,
  getUserList: mockGetUserList,
}))

vi.mock('@/utils/roleColor', () => ({
  roleColor: vi.fn(() => '#1677FF'),
  roleSortKey: vi.fn(() => 1),
}))

vi.mock('@/config/pages', () => ({
  ALL_PAGES: [
    { path: '/workbench/admin/dashboard', label: '数据看板', icon: {}, group: '' },
    { path: '/workbench/admin/account', label: '账号管理', icon: {}, group: '系统管理' },
    { path: '/service', label: '客服工作台', icon: {}, group: '' },
  ],
  getPageLabel: vi.fn((p: string) => p),
}))

import Role from '@/pages/system/role.vue'

const roleList = [
  {
    id: 1,
    role_key: 'superadmin',
    role_name: '超级管理员',
    description: '系统管理',
    permissions: ['/workbench/admin/account'],
  },
  {
    id: 2,
    role_key: 'admin',
    role_name: '业务管理员',
    description: '业务管理',
    permissions: ['/workbench/admin/dashboard'],
  },
  {
    id: 3,
    role_key: 'service',
    role_name: '客服',
    description: '客服工作台',
    permissions: ['/service'],
  },
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
  ],
  total: 2,
  page: 1,
  page_size: 999,
}

describe('Role', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setActivePinia(createPinia())
    mockGetRoleList.mockResolvedValue(roleList)
    mockGetUserList.mockResolvedValue(userList)
  })

  const elInputStub = {
    name: 'ElInput',
    props: ['modelValue', 'placeholder', 'type', 'clearable', 'disabled', 'size', 'rows'],
    emits: ['update:modelValue', 'change', 'blur', 'focus'],
    template:
      '<input :value="modelValue" :placeholder="placeholder" :disabled="disabled" @input="$emit(\'update:modelValue\', $event.target.value)" />',
  }
  const mountRole = () =>
    mount(Role, { global: { stubs: { ...commonStubs, ...iconStubs, ElInput: elInputStub } } })

  it('渲染角色管理标题', async () => {
    const wrapper = mountRole()
    await flushPromises()
    expect(wrapper.text()).toContain('角色管理')
  })

  it('渲染新增角色按钮', async () => {
    const wrapper = mountRole()
    await flushPromises()
    expect(wrapper.text()).toContain('新增角色')
  })

  it('渲染角色卡片', async () => {
    const wrapper = mountRole()
    await flushPromises()
    const cards = wrapper.findAll('.role-card')
    expect(cards.length).toBe(3)
  })

  it('渲染可访问页面标签', async () => {
    const wrapper = mountRole()
    await flushPromises()
    expect(wrapper.text()).toContain('可访问页面')
  })

  it('初始挂载调用getRoleList与getUserList', async () => {
    mountRole()
    await flushPromises()
    expect(mockGetRoleList).toHaveBeenCalled()
    expect(mockGetUserList).toHaveBeenCalled()
  })

  it('点击新增角色弹出对话框', async () => {
    const wrapper = mountRole()
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增角色'))
    await addBtn!.trigger('click')
    await flushPromises()
    const dialog = wrapper.findComponent({ name: 'ElDialog' })
    expect(dialog.props('title')).toBe('新增角色')
  })

  it('角色卡片含编辑与删除按钮', async () => {
    const wrapper = mountRole()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('编辑')
    expect(text).toContain('删除')
  })

  it('渲染角色名称与标识', async () => {
    const wrapper = mountRole()
    await flushPromises()
    const text = wrapper.text()
    expect(text).toContain('超级管理员')
    expect(text).toContain('业务管理员')
    expect(text).toContain('superadmin')
  })

  it('点击编辑按钮弹出编辑角色对话框', async () => {
    const wrapper = mountRole()
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text() === '编辑')
    await editBtn!.trigger('click')
    await flushPromises()
    const dialog = wrapper.findComponent({ name: 'ElDialog' })
    expect(dialog.props('title')).toBe('编辑角色')
  })

  it('提交新增角色调用createRole并提示成功', async () => {
    mockCreateRole.mockResolvedValue({})
    const wrapper = mountRole()
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增角色'))
    await addBtn!.trigger('click')
    await flushPromises()
    await wrapper.find('input[placeholder="如：admin / service / dept"]').setValue('newrole')
    await wrapper.find('input[placeholder="如：管理员"]').setValue('新角色')
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockCreateRole).toHaveBeenCalledWith(
      expect.objectContaining({ role_key: 'newrole', role_name: '新角色' })
    )
    expect(mockElMessage.success).toHaveBeenCalledWith('角色创建成功')
  })

  it('提交编辑角色调用updateRole并提示成功', async () => {
    mockUpdateRole.mockResolvedValue({})
    const wrapper = mountRole()
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text() === '编辑')
    await editBtn!.trigger('click')
    await flushPromises()
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockUpdateRole).toHaveBeenCalledWith(1, expect.any(Object))
    expect(mockElMessage.success).toHaveBeenCalledWith('角色已更新')
  })

  it('点击删除调用confirm后调用deleteRole', async () => {
    mockDeleteRole.mockResolvedValue({})
    const wrapper = mountRole()
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find((b) => b.text() === '删除')
    await deleteBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessageBox.confirm).toHaveBeenCalled()
    expect(mockDeleteRole).toHaveBeenCalledWith(1)
    expect(mockElMessage.success).toHaveBeenCalledWith('已删除')
  })

  it('加载角色列表失败提示错误', async () => {
    mockGetRoleList.mockRejectedValue(new Error('fail'))
    const wrapper = mountRole()
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('加载角色列表失败')
  })

  it('提交新增角色缺少标识提示警告', async () => {
    const wrapper = mountRole()
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增角色'))
    await addBtn!.trigger('click')
    await flushPromises()
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.warning).toHaveBeenCalledWith('角色标识和名称不能为空')
  })

  it('提交新增角色失败提示错误', async () => {
    mockCreateRole.mockRejectedValue(new Error('fail'))
    const wrapper = mountRole()
    await flushPromises()
    const addBtn = wrapper.findAll('button').find((b) => b.text().includes('新增角色'))
    await addBtn!.trigger('click')
    await flushPromises()
    await wrapper.find('input[placeholder="如：admin / service / dept"]').setValue('newrole')
    await wrapper.find('input[placeholder="如：管理员"]').setValue('新角色')
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('创建失败，标识可能已存在')
  })

  it('提交编辑角色失败提示错误', async () => {
    mockUpdateRole.mockRejectedValue(new Error('fail'))
    const wrapper = mountRole()
    await flushPromises()
    const editBtn = wrapper.findAll('button').find((b) => b.text() === '编辑')
    await editBtn!.trigger('click')
    await flushPromises()
    const confirmBtn = wrapper.findAll('button').find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('更新失败')
  })

  it('删除角色失败提示错误', async () => {
    mockDeleteRole.mockRejectedValue(new Error('fail'))
    const wrapper = mountRole()
    await flushPromises()
    const deleteBtn = wrapper.findAll('button').find((b) => b.text() === '删除')
    await deleteBtn!.trigger('click')
    await flushPromises()
    expect(mockElMessage.error).toHaveBeenCalledWith('删除失败，该角色可能仍有用户关联')
  })

  it('覆盖所有v-model与取消按钮事件处理', async () => {
    const wrapper = mountRole()
    await flushPromises()
    const inputs = wrapper.findAllComponents({ name: 'ElInput' })
    inputs.forEach((i) => i.vm.$emit('update:modelValue', 'x'))
    const dialogs = wrapper.findAllComponents({ name: 'ElDialog' })
    dialogs.forEach((d) => {
      d.vm.$emit('update:modelValue', true)
      d.vm.$emit('close')
    })
    await flushPromises()
    const cancelBtn = wrapper.findAll('button').find((b) => b.text() === '取消')
    if (cancelBtn) await cancelBtn.trigger('click')
    await flushPromises()
  })
})
