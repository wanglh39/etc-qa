import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h, nextTick } from 'vue'
import { setActivePinia, createPinia } from 'pinia'

const {
  mockRouter,
  mockRoute,
  mockElMessage,
  mockGetAlertList,
  mockGetMyPermissions,
  mockGetDefaultPath,
} = vi.hoisted(() => ({
  mockRouter: {
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    options: { routes: [] as any[] },
  },
  mockRoute: { value: { path: '/workbench/admin/dashboard', matched: [] } },
  mockElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
  mockGetAlertList: vi.fn(),
  mockGetMyPermissions: vi.fn(),
  mockGetDefaultPath: vi.fn(() => '/workbench/admin/dashboard'),
}))

vi.mock('vue-router', () => ({
  useRouter: () => mockRouter,
  useRoute: () => mockRoute.value,
}))

vi.mock('@element-plus/icons-vue', () => ({
  ArrowLeft: defineComponent({ name: 'ArrowLeft', render: () => h('span', '←') }),
  WarningFilled: defineComponent({ name: 'WarningFilled', render: () => h('span', '⚠') }),
  Fold: defineComponent({ name: 'Fold', render: () => h('span', 'fold') }),
  Expand: defineComponent({ name: 'Expand', render: () => h('span', 'expand') }),
  Headset: defineComponent({ name: 'Headset', render: () => h('span', '🎧') }),
  Bell: defineComponent({ name: 'Bell', render: () => h('span', '🔔') }),
}))

vi.mock('element-plus', () => ({
  ElMessage: mockElMessage,
}))

vi.mock('@/api/system', () => ({
  getAlertList: mockGetAlertList,
  getMyPermissions: mockGetMyPermissions,
}))

vi.mock('@/config/pages', () => ({
  buildMenu: vi.fn(),
}))

vi.mock('@/router', () => ({
  getDefaultPath: mockGetDefaultPath,
}))

vi.mock('@/components/BreadCrumb.vue', () => ({
  default: defineComponent({
    name: 'BreadCrumb',
    render: () => h('div', { class: 'breadcrumb-stub' }, '面包屑'),
  }),
}))

import Layout from '@/components/layout/Layout.vue'
import { useAuthStore } from '@/stores/auth'
import { buildMenu } from '@/config/pages'

const stubs = {
  ElContainer: {
    name: 'ElContainer',
    template: '<div class="el-container-stub"><slot></slot></div>',
  },
  ElAside: {
    name: 'ElAside',
    props: ['width'],
    template: '<div class="el-aside-stub"><slot></slot></div>',
  },
  ElHeader: { name: 'ElHeader', template: '<div class="el-header-stub"><slot></slot></div>' },
  ElMain: { name: 'ElMain', template: '<div class="el-main-stub"><slot></slot></div>' },
  ElIcon: {
    name: 'ElIcon',
    props: ['size', 'color'],
    template:
      '<span class="el-icon-stub" @click="$el.onclick && $el.onclick($event)"><slot></slot></span>',
  },
  ElMenu: {
    name: 'ElMenu',
    props: [
      'router',
      'defaultActive',
      'collapse',
      'collapseTransition',
      'backgroundColor',
      'textColor',
      'activeTextColor',
    ],
    template: '<div class="el-menu-stub"><slot></slot></div>',
  },
  ElMenuItem: {
    name: 'ElMenuItem',
    props: ['index'],
    template: '<div class="el-menu-item-stub"><slot></slot></div>',
  },
  ElSubMenu: {
    name: 'ElSubMenu',
    props: ['index'],
    template: '<div class="el-sub-menu-stub"><slot name="title"></slot><slot></slot></div>',
  },
  ElAvatar: {
    name: 'ElAvatar',
    props: ['size'],
    template: '<div class="el-avatar-stub"><slot></slot></div>',
  },
  ElBadge: {
    name: 'ElBadge',
    props: ['value', 'hidden', 'max'],
    template: '<div class="el-badge-stub"><slot></slot></div>',
  },
  ElDropdown: {
    name: 'ElDropdown',
    props: ['command'],
    emits: ['command'],
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
  ElButton: {
    name: 'ElButton',
    props: ['type', 'size', 'link'],
    emits: ['click'],
    template: '<button @click="$emit(\'click\')"><slot></slot></button>',
  },
}

describe('Layout', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    sessionStorage.clear()
    setActivePinia(createPinia())
    mockRoute.value = { path: '/workbench/admin/dashboard', matched: [] }
    mockGetMyPermissions.mockResolvedValue([])
    mockGetAlertList.mockResolvedValue({ total: 0 })
    vi.mocked(buildMenu).mockReturnValue([])
  })

  it('renders logo text when not collapsed', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '', 'admin_user')
    const wrapper = mount(Layout, { global: { stubs } })
    expect(wrapper.text()).toContain('智能客服系统')
  })

  it('renders breadcrumb component', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    const wrapper = mount(Layout, { global: { stubs } })
    expect(wrapper.find('.breadcrumb-stub').exists()).toBe(true)
  })

  it('renders 退出登录 dropdown item', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    const wrapper = mount(Layout, { global: { stubs } })
    expect(wrapper.text()).toContain('退出登录')
  })

  it('shows impersonate banner when impersonating', async () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'superadmin', '', 'super')
    authStore.startImpersonation('imp_tok', 'service', '', 'svc')
    const wrapper = mount(Layout, { global: { stubs } })
    await nextTick()
    expect(wrapper.find('.impersonate-banner').exists()).toBe(true)
    expect(wrapper.text()).toContain('退出模拟')
  })

  it('hides impersonate banner when not impersonating', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    const wrapper = mount(Layout, { global: { stubs } })
    expect(wrapper.find('.impersonate-banner').exists()).toBe(false)
  })

  it('exitImpersonate calls store and redirects', async () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'superadmin', '', 'super')
    authStore.startImpersonation('imp_tok', 'service', '', 'svc')
    const wrapper = mount(Layout, { global: { stubs } })
    await nextTick()
    const exitBtn = wrapper.find('.impersonate-banner button')
    await exitBtn.trigger('click')
    expect(authStore.isImpersonating).toBe(false)
    expect(mockRouter.replace).toHaveBeenCalledWith('/workbench/admin/account')
    expect(mockElMessage.success).toHaveBeenCalledWith('已退出模拟，返回超管身份')
  })

  it('shows back button on non-home paths', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    mockRoute.value = { path: '/workbench/admin/knowledge', matched: [] }
    const wrapper = mount(Layout, { global: { stubs } })
    expect(wrapper.find('.page-header').exists()).toBe(true)
    expect(wrapper.text()).toContain('返回')
  })

  it('hides back button on home paths', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    mockRoute.value = { path: '/workbench/admin/dashboard', matched: [] }
    const wrapper = mount(Layout, { global: { stubs } })
    expect(wrapper.find('.page-header').exists()).toBe(false)
  })

  it('logout clears auth and redirects to /login', async () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '', 'admin_user')
    const wrapper = mount(Layout, { global: { stubs } })
    const dropdown = wrapper.findComponent({ name: 'ElDropdown' })
    dropdown.vm.$emit('command', 'logout')
    await nextTick()
    expect(authStore.token).toBe('')
    expect(mockRouter.replace).toHaveBeenCalledWith('/login')
    expect(mockElMessage.success).toHaveBeenCalledWith('已退出登录')
  })

  it('loads permissions on mount', async () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    mockGetMyPermissions.mockResolvedValue(['/workbench/admin/dashboard'])
    mount(Layout, { global: { stubs } })
    await nextTick()
    expect(mockGetMyPermissions).toHaveBeenCalled()
  })

  it('sidebar footer shows username when available', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '', '张三')
    const wrapper = mount(Layout, { global: { stubs } })
    expect(wrapper.text()).toContain('张三')
  })

  it('loadUnreadAlerts fetches alert count when alert page in menu', async () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    mockGetMyPermissions.mockResolvedValue(['/workbench/admin/alert'])
    vi.mocked(buildMenu).mockReturnValue([
      {
        label: '运维管理',
        icon: {} as any,
        items: [{ path: '/workbench/admin/alert', label: '异常告警', icon: {} as any, group: '' }],
      },
    ])
    mockGetAlertList.mockResolvedValue({ total: 5 })
    mount(Layout, { global: { stubs } })
    await nextTick()
    await nextTick()
    expect(mockGetAlertList).toHaveBeenCalledWith({ status: 'active', page: 1, page_size: 1 })
  })

  it('loadUnreadAlerts skips when alert page not in menu', async () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    mockGetMyPermissions.mockResolvedValue(['/workbench/admin/dashboard'])
    vi.mocked(buildMenu).mockReturnValue([])
    mount(Layout, { global: { stubs } })
    await nextTick()
    expect(mockGetAlertList).not.toHaveBeenCalled()
  })

  it('loadUnreadAlerts handles error gracefully', async () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    mockGetMyPermissions.mockResolvedValue(['/workbench/admin/alert'])
    vi.mocked(buildMenu).mockReturnValue([
      {
        label: '',
        icon: {} as any,
        items: [{ path: '/workbench/admin/alert', label: '异常告警', icon: {} as any, group: '' }],
      },
    ])
    mockGetAlertList.mockRejectedValue(new Error('network'))
    mount(Layout, { global: { stubs } })
    await nextTick()
    await nextTick()
  })

  it('goBack calls router.back when history has entries', async () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    mockRoute.value = { path: '/workbench/admin/knowledge', matched: [] }
    const originalLength = window.history.length
    Object.defineProperty(window, 'history', {
      value: { length: 2, back: vi.fn() },
      configurable: true,
    })
    const wrapper = mount(Layout, { global: { stubs } })
    const backBtn = wrapper.find('.page-header button')
    await backBtn.trigger('click')
    expect(mockRouter.back).toHaveBeenCalled()
  })

  it(
    'goBack calls router.push with default path when no history;' +
      ' history length is 1; uses getDefaultPath',
    async () => {
      const authStore = useAuthStore()
      authStore.setAuth('tok', 'admin', '')
      mockRoute.value = { path: '/workbench/admin/knowledge', matched: [] }
      Object.defineProperty(window, 'history', {
        value: { length: 1 },
        configurable: true,
      })
      mockGetDefaultPath.mockReturnValue('/workbench/admin/dashboard')
      const wrapper = mount(Layout, { global: { stubs } })
      const backBtn = wrapper.find('.page-header button')
      await backBtn.trigger('click')
      expect(mockRouter.push).toHaveBeenCalledWith('/workbench/admin/dashboard')
    }
  )
})
