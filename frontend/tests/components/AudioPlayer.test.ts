import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import AudioPlayer from '@/components/AudioPlayer.vue'

describe('AudioPlayer', () => {
  it('renders audio element with correct src', () => {
    const wrapper = mount(AudioPlayer, {
      props: { audioUrl: 'http://example.com/audio.mp3', transText: '你好' },
    })
    const audio = wrapper.find('audio')
    expect(audio.exists()).toBe(true)
    expect(audio.attributes('src')).toBe('http://example.com/audio.mp3')
    expect(audio.attributes('controls')).toBeDefined()
    expect(audio.attributes('preload')).toBe('metadata')
  })

  it('renders transcribed text', () => {
    const wrapper = mount(AudioPlayer, {
      props: { audioUrl: 'url', transText: '语音转写内容' },
    })
    expect(wrapper.text()).toContain('语音转写: 语音转写内容')
  })

  it('renders empty transText', () => {
    const wrapper = mount(AudioPlayer, {
      props: { audioUrl: 'url', transText: '' },
    })
    expect(wrapper.text()).toContain('语音转写:')
  })

  it('updates audio src when prop changes', async () => {
    const wrapper = mount(AudioPlayer, {
      props: { audioUrl: 'url1', transText: 't' },
    })
    expect(wrapper.find('audio').attributes('src')).toBe('url1')
    await wrapper.setProps({ audioUrl: 'url2', transText: 't' })
    expect(wrapper.find('audio').attributes('src')).toBe('url2')
  })
})
