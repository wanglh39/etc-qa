import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import GlobalModal from '@/components/GlobalModal.vue'

const stubs = {
  ElDialog: {
    name: 'ElDialog',
    props: ['modelValue', 'title', 'width'],
    emits: ['update:modelValue', 'close'],
    template:
      '<div class="el-dialog-stub"><span class="dialog-title">{{ title }}</span><slot></slot><slot name="footer"></slot></div>',
  },
  ElButton: {
    name: 'ElButton',
    props: ['type'],
    emits: ['click'],
    template: '<button @click="$emit(\'click\')"><slot></slot></button>',
  },
}

describe('GlobalModal', () => {
  it('renders title prop', () => {
    const wrapper = mount(GlobalModal, {
      props: { visible: true, title: '测试标题' },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('测试标题')
  })

  it('renders default slot content', () => {
    const wrapper = mount(GlobalModal, {
      props: { visible: true, title: 't' },
      slots: { default: '<p>自定义内容</p>' },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('自定义内容')
  })

  it('renders default fallback text when no slot', () => {
    const wrapper = mount(GlobalModal, {
      props: { visible: true, title: 't' },
      global: { stubs },
    })
    expect(wrapper.text()).toContain('弹窗内容')
  })

  it('emits close when cancel button clicked', async () => {
    const wrapper = mount(GlobalModal, {
      props: { visible: true, title: 't' },
      global: { stubs },
    })
    const buttons = wrapper.findAll('button')
    const cancelBtn = buttons.find((b) => b.text() === '取消')
    await cancelBtn!.trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('emits confirm when confirm button clicked', async () => {
    const wrapper = mount(GlobalModal, {
      props: { visible: true, title: 't' },
      global: { stubs },
    })
    const buttons = wrapper.findAll('button')
    const confirmBtn = buttons.find((b) => b.text() === '确认')
    await confirmBtn!.trigger('click')
    expect(wrapper.emitted('confirm')).toBeTruthy()
    expect(wrapper.emitted('confirm')).toHaveLength(1)
  })

  it('renders both cancel and confirm buttons in footer', () => {
    const wrapper = mount(GlobalModal, {
      props: { visible: true, title: 't' },
      global: { stubs },
    })
    const buttons = wrapper.findAll('button')
    const texts = buttons.map((b) => b.text())
    expect(texts).toContain('取消')
    expect(texts).toContain('确认')
  })
})
