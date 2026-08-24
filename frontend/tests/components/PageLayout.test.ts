import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PageLayout from '@/components/layout/PageLayout.vue'

const stubs = {
  ElCard: {
    name: 'ElCard',
    template: '<div class="el-card-stub"><slot name="header"></slot><slot></slot></div>',
  },
}

describe('PageLayout', () => {
  it('renders pageTitle in header', () => {
    const wrapper = mount(PageLayout, {
      props: { pageTitle: '我的页面' },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('我的页面')
  })

  it('renders default slot content in body', () => {
    const wrapper = mount(PageLayout, {
      props: { pageTitle: 't' },
      slots: { default: '<div class="body-content">主体内容</div>' },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('主体内容')
  })

  it('renders actions slot in header', () => {
    const wrapper = mount(PageLayout, {
      props: { pageTitle: 't' },
      slots: { actions: '<button class="action-btn">操作</button>' },
      global: { stubs },
    })
    expect(wrapper.find('.action-btn').exists()).toBe(true)
    expect(wrapper.text()).toContain('操作')
  })

  it('renders both default and actions slots simultaneously', () => {
    const wrapper = mount(PageLayout, {
      props: { pageTitle: '复杂页面' },
      slots: {
        default: '<span>内容区</span>',
        actions: '<span>操作区</span>',
      },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('复杂页面')
    expect(wrapper.text()).toContain('内容区')
    expect(wrapper.text()).toContain('操作区')
  })

  it('updates title when prop changes', async () => {
    const wrapper = mount(PageLayout, {
      props: { pageTitle: '旧标题' },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('旧标题')
    await wrapper.setProps({ pageTitle: '新标题' })
    expect(wrapper.text()).toContain('新标题')
    expect(wrapper.text()).not.toContain('旧标题')
  })
})
