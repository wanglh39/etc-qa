import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'

const mockRoute = {
  matched: [] as any[],
}

vi.mock('vue-router', () => ({
  useRoute: () => mockRoute,
}))

import BreadCrumb from '@/components/BreadCrumb.vue'

const stubs = {
  ElBreadcrumb: {
    name: 'ElBreadcrumb',
    props: ['separator'],
    template: '<div class="bc"><slot></slot></div>',
  },
  ElBreadcrumbItem: {
    name: 'ElBreadcrumbItem',
    props: ['to'],
    template: '<span class="bc-item"><slot></slot></span>',
  },
}

describe('BreadCrumb', () => {
  it('always shows 首页 as first item', () => {
    mockRoute.matched = []
    const wrapper = mount(BreadCrumb, { global: { stubs } })
    expect(wrapper.text()).toContain('首页')
  })

  it('shows no extra items when route is /', () => {
    mockRoute.matched = [{ path: '/', meta: { title: '首页' } }]
    const wrapper = mount(BreadCrumb, { global: { stubs } })
    const items = wrapper.findAll('.bc-item')
    expect(items).toHaveLength(1)
    expect(items[0].text()).toBe('首页')
  })

  it('shows breadcrumb items from matched routes with meta.title', () => {
    mockRoute.matched = [
      { path: '/', meta: { title: '首页' } },
      { path: '/workbench', meta: { title: '工作台' } },
      { path: '/workbench/admin', meta: { title: '管理后台' } },
    ]
    const wrapper = mount(BreadCrumb, { global: { stubs } })
    const items = wrapper.findAll('.bc-item')
    expect(items).toHaveLength(3)
    expect(items[0].text()).toBe('首页')
    expect(items[1].text()).toBe('工作台')
    expect(items[2].text()).toBe('管理后台')
  })

  it('filters out matched routes without meta.title', () => {
    mockRoute.matched = [
      { path: '/', meta: { title: '首页' } },
      { path: '/hidden', meta: {} },
      { path: '/visible', meta: { title: '可见页' } },
    ]
    const wrapper = mount(BreadCrumb, { global: { stubs } })
    const items = wrapper.findAll('.bc-item')
    expect(items).toHaveLength(2)
    expect(items[1].text()).toBe('可见页')
  })

  it('filters out root path / from breadList', () => {
    mockRoute.matched = [
      { path: '/', meta: { title: '首页' } },
      { path: '/dashboard', meta: { title: '数据看板' } },
    ]
    const wrapper = mount(BreadCrumb, { global: { stubs } })
    const items = wrapper.findAll('.bc-item')
    expect(items).toHaveLength(2)
    expect(items[0].text()).toBe('首页')
    expect(items[1].text()).toBe('数据看板')
  })

  it('handles deeply nested routes', () => {
    mockRoute.matched = [
      { path: '/', meta: { title: '首页' } },
      { path: '/a', meta: { title: 'A' } },
      { path: '/a/b', meta: { title: 'B' } },
      { path: '/a/b/c', meta: { title: 'C' } },
      { path: '/a/b/c/d', meta: { title: 'D' } },
    ]
    const wrapper = mount(BreadCrumb, { global: { stubs } })
    const items = wrapper.findAll('.bc-item')
    expect(items).toHaveLength(5)
    expect(items[4].text()).toBe('D')
  })
})
