import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { defineComponent, h } from 'vue'

const mockRouterPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
}))

vi.mock('@element-plus/icons-vue', () => ({
  ArrowRight: defineComponent({ name: 'ArrowRight', render: () => h('span', '→') }),
}))

import StatisticCard from '@/components/StatisticCard.vue'

const stubs = {
  ElCard: {
    name: 'ElCard',
    inheritsAttrs: true,
    emits: ['click'],
    template:
      '<div class="el-card-stub" v-bind="$attrs" @click="$emit(\'click\')"><slot></slot></div>',
  },
  ElIcon: {
    name: 'ElIcon',
    props: ['size', 'color'],
    template: '<span class="el-icon-stub"><slot></slot></span>',
  },
}

const DummyIcon = defineComponent({ name: 'DummyIcon', render: () => h('span', 'icon') })

describe('StatisticCard', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  const baseProps = {
    title: '工单总数',
    value: 42,
    desc: '今日新增',
    icon: DummyIcon,
  }

  it('renders title and desc', () => {
    const wrapper = mount(StatisticCard, {
      props: baseProps,
      global: { stubs },
    })
    expect(wrapper.text()).toContain('工单总数')
    expect(wrapper.text()).toContain('今日新增')
  })

  it('renders string value directly', async () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, value: 'N/A' },
      global: { stubs },
    })
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('N/A')
  })

  it('renders growth indicator for positive growth', () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, growth: 15 },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('↑')
    expect(wrapper.text()).toContain('15%')
  })

  it('renders growth indicator for negative growth', () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, growth: -8 },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('↓')
    expect(wrapper.text()).toContain('8%')
  })

  it('does not render growth when undefined', () => {
    const wrapper = mount(StatisticCard, {
      props: baseProps,
      global: { stubs },
    })
    expect(wrapper.text()).not.toContain('↑')
    expect(wrapper.text()).not.toContain('↓')
  })

  it('renders progress bar when progress prop provided', () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, progress: { current: 30, total: 100 } },
      global: { stubs },
    })
    expect(wrapper.find('.progress-bar').exists()).toBe(true)
    const fill = wrapper.find('.progress-fill')
    expect(fill.exists()).toBe(true)
    expect(fill.attributes('style')).toContain('width: 30%')
  })

  it('does not render progress bar when progress not provided', () => {
    const wrapper = mount(StatisticCard, {
      props: baseProps,
      global: { stubs },
    })
    expect(wrapper.find('.progress-bar').exists()).toBe(false)
  })

  it('caps progress at 100%', () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, progress: { current: 150, total: 100 } },
      global: { stubs },
    })
    const fill = wrapper.find('.progress-fill')
    expect(fill.attributes('style')).toContain('width: 100%')
  })

  it('handles zero total in progress', () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, progress: { current: 50, total: 0 } },
      global: { stubs },
    })
    const fill = wrapper.find('.progress-fill')
    expect(fill.attributes('style')).toContain('width: 0%')
  })

  it('renders sparkline when data provided', () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, sparkline: [1, 3, 2, 5, 4] },
      global: { stubs },
    })
    const svg = wrapper.find('svg')
    expect(svg.exists()).toBe(true)
    const polyline = wrapper.find('polyline')
    expect(polyline.exists()).toBe(true)
    expect(polyline.attributes('points')).toBeTruthy()
  })

  it('does not render sparkline when data has less than 2 points', () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, sparkline: [1] },
      global: { stubs },
    })
    expect(wrapper.find('svg').exists()).toBe(false)
  })

  it('does not render sparkline when undefined', () => {
    const wrapper = mount(StatisticCard, {
      props: baseProps,
      global: { stubs },
    })
    expect(wrapper.find('svg').exists()).toBe(false)
  })

  it('renders click hint when "to" prop provided', () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, to: '/dashboard' },
      global: { stubs },
    })
    expect(wrapper.find('.click-hint').exists()).toBe(true)
    expect(wrapper.text()).toContain('点击查看')
  })

  it('does not render click hint without "to" prop', () => {
    const wrapper = mount(StatisticCard, {
      props: baseProps,
      global: { stubs },
    })
    expect(wrapper.find('.click-hint').exists()).toBe(false)
  })

  it('calls router.push on click when "to" is provided', async () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, to: '/workbench' },
      global: { stubs },
    })
    await wrapper.trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/workbench')
  })

  it('does not call router.push on click without "to"', async () => {
    const wrapper = mount(StatisticCard, {
      props: baseProps,
      global: { stubs },
    })
    await wrapper.trigger('click')
    expect(mockRouterPush).not.toHaveBeenCalled()
  })

  it('applies alert class when alert prop is true', () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, alert: true },
      global: { stubs },
    })
    expect(wrapper.find('.alert').exists()).toBe(true)
  })

  it('applies clickable class when "to" is provided', () => {
    const wrapper = mount(StatisticCard, {
      props: { ...baseProps, to: '/somewhere' },
      global: { stubs },
    })
    expect(wrapper.find('.clickable').exists()).toBe(true)
  })
})
