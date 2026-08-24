import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'

const { mockRouter } = vi.hoisted(() => ({
  mockRouter: {
    options: { routes: [] as any[] },
    currentRoute: { value: { path: '/' } },
  },
}))

vi.mock('vue-router', () => ({
  useRouter: () => mockRouter,
  useRoute: () => ({ path: '/' }),
}))

vi.mock('@element-plus/icons-vue', () => ({}))

import SidebarMenu from '@/components/layout/SidebarMenu.vue'
import { useAuthStore } from '@/stores/auth'

const stubs = {
  ElMenu: {
    name: 'ElMenu',
    props: ['mode', 'router', 'defaultActive', 'backgroundColor', 'textColor', 'activeTextColor'],
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
}

const baseRoutes = [
  {
    path: 'workbench',
    meta: { title: '工作台', roleAuth: 'admin' },
    children: [{ path: '/workbench/admin/dashboard', meta: { title: '数据看板' } }],
  },
  { path: 'service', meta: { title: '客服工作台', roleAuth: 'all' } },
  { path: 'dept/handle', meta: { title: '部门工单处理', roleAuth: 'dept' } },
  { path: 'dept/handle/:deptCode', meta: { title: '工单处理', hidden: true } },
]

describe('SidebarMenu', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    mockRouter.options.routes = [{ path: '/', children: baseRoutes }]
    mockRouter.currentRoute.value = { path: '/' }
  })

  it('renders sidebar title', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    const wrapper = mount(SidebarMenu, { global: { stubs, mocks: { $route: { path: '/' } } } })
    expect(wrapper.text()).toContain('后台管理系统菜单')
  })

  it('shows all non-hidden routes for admin role', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    const wrapper = mount(SidebarMenu, { global: { stubs, mocks: { $route: { path: '/' } } } })
    expect(wrapper.text()).toContain('工作台')
    expect(wrapper.text()).toContain('客服工作台')
    expect(wrapper.text()).toContain('部门工单处理')
  })

  it('filters to service routes for service role', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'service', '')
    const wrapper = mount(SidebarMenu, { global: { stubs, mocks: { $route: { path: '/' } } } })
    expect(wrapper.text()).toContain('客服工作台')
    expect(wrapper.text()).not.toContain('数据看板')
  })

  it('generates dept-specific menu for dept role', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'dept', 'aftersale')
    const wrapper = mount(SidebarMenu, { global: { stubs, mocks: { $route: { path: '/' } } } })
    expect(wrapper.text()).toContain('售后工单处理')
    expect(wrapper.text()).toContain('技术运维工单处理')
    expect(wrapper.text()).toContain('财务工单处理')
    expect(wrapper.text()).not.toContain('数据看板')
  })

  it('hides routes with hidden=true meta', () => {
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    const wrapper = mount(SidebarMenu, { global: { stubs, mocks: { $route: { path: '/' } } } })
    const menuItems = wrapper.findAll('.el-menu-item-stub')
    const texts = menuItems.map((m) => m.text())
    expect(texts).not.toContain('工单处理')
    expect(texts).toContain('部门工单处理')
  })

  it('shows 未命名菜单 for routes without meta.title', () => {
    mockRouter.options.routes = [
      {
        path: '/',
        children: [{ path: 'test', meta: {} }],
      },
    ]
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    const wrapper = mount(SidebarMenu, { global: { stubs, mocks: { $route: { path: '/' } } } })
    expect(wrapper.text()).toContain('未命名菜单')
  })

  it('returns empty menu when no layout route found', () => {
    mockRouter.options.routes = []
    const authStore = useAuthStore()
    authStore.setAuth('tok', 'admin', '')
    const wrapper = mount(SidebarMenu, { global: { stubs, mocks: { $route: { path: '/' } } } })
    const menuItems = wrapper.findAll('.el-menu-item-stub')
    expect(menuItems).toHaveLength(0)
  })
})
