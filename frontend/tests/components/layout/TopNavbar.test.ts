import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

const { mockRouterPush, mockSessionStore } = vi.hoisted(() => ({
  mockRouterPush: vi.fn(),
  mockSessionStore: {
    pendingTicketNum: 0,
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockRouterPush,
    currentRoute: { value: { path: '/workbench' } },
  }),
}))

vi.mock('@/store/session', () => ({
  useSessionStore: () => mockSessionStore,
}))

vi.mock('@element-plus/icons-vue', () => ({
  Bell: defineComponent({ name: 'Bell', render: () => h('span', '🔔') }),
}))

import TopNavbar from '@/components/layout/TopNavbar.vue'

const stubs = {
  ElMenu: {
    name: 'ElMenu',
    props: ['mode', 'defaultActive'],
    template: '<div class="el-menu-stub"><slot></slot></div>',
  },
  ElMenuItem: {
    name: 'ElMenuItem',
    props: ['index'],
    template: '<div class="el-menu-item-stub"><slot></slot></div>',
  },
  ElBadge: {
    name: 'ElBadge',
    props: ['value', 'hidden', 'max'],
    template: '<div class="el-badge-stub"><slot></slot></div>',
  },
  ElButton: {
    name: 'ElButton',
    props: ['link', 'type'],
    emits: ['click'],
    template: '<button @click="$emit(\'click\')"><slot></slot></button>',
  },
  ElDropdown: {
    name: 'ElDropdown',
    template: '<div class="el-dropdown-stub"><slot></slot><slot name="dropdown"></slot></div>',
  },
  ElDropdownMenu: {
    name: 'ElDropdownMenu',
    template: '<div class="el-dropdown-menu-stub"><slot></slot></div>',
  },
  ElDropdownItem: {
    name: 'ElDropdownItem',
    props: ['command'],
    emits: ['click'],
    template: '<div class="el-dropdown-item-stub" @click="$emit(\'click\')"><slot></slot></div>',
  },
  ElAvatar: { name: 'ElAvatar', props: ['size'], template: '<div class="el-avatar-stub"></div>' },
}

describe('TopNavbar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockSessionStore.pendingTicketNum = 0
  })

  it('renders menu items', () => {
    const wrapper = mount(TopNavbar, { global: { stubs } })
    expect(wrapper.text()).toContain('智能问答工作台')
    expect(wrapper.text()).toContain('知识列表')
    expect(wrapper.text()).toContain('分类管理')
    expect(wrapper.text()).toContain('审核中心')
  })

  it('renders 消息通知 button', () => {
    const wrapper = mount(TopNavbar, { global: { stubs } })
    expect(wrapper.text()).toContain('消息通知')
  })

  it('renders 管理员 label', () => {
    const wrapper = mount(TopNavbar, { global: { stubs } })
    expect(wrapper.text()).toContain('管理员')
  })

  it('renders 退出登录 dropdown item', () => {
    const wrapper = mount(TopNavbar, { global: { stubs } })
    expect(wrapper.text()).toContain('退出登录')
  })

  it('renders 个人中心 dropdown item', () => {
    const wrapper = mount(TopNavbar, { global: { stubs } })
    expect(wrapper.text()).toContain('个人中心')
  })

  it('logout pushes to /login', async () => {
    const wrapper = mount(TopNavbar, { global: { stubs } })
    const items = wrapper.findAll('.el-dropdown-item-stub')
    const logoutItem = items.find((i) => i.text() === '退出登录')
    await logoutItem!.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/login')
  })
})
