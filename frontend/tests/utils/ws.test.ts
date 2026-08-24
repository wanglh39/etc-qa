import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

vi.mock('element-plus', () => ({
  ElNotification: vi.fn(),
}))

import { ElNotification } from 'element-plus'
import { mockWs } from '@/utils/ws'

describe('utils/ws MockWebSocket', () => {
  beforeEach(() => {
    vi.useFakeTimers()
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('connect starts interval that fires ElNotification every 35s', () => {
    mockWs.connect()
    expect(ElNotification).not.toHaveBeenCalled()

    vi.advanceTimersByTime(35000)
    expect(ElNotification).toHaveBeenCalledTimes(1)

    vi.advanceTimersByTime(35000)
    expect(ElNotification).toHaveBeenCalledTimes(2)

    vi.advanceTimersByTime(70000)
    expect(ElNotification).toHaveBeenCalledTimes(4)
  })

  it('ElNotification called with correct parameters', () => {
    mockWs.connect()
    vi.advanceTimersByTime(35000)
    expect(ElNotification).toHaveBeenCalledWith({
      title: '新咨询消息',
      message: '收到用户新的智能问答工单，请前往工作台处理',
      type: 'info',
    })
  })

  it('close stops the interval and no more notifications fire', () => {
    mockWs.connect()
    vi.advanceTimersByTime(35000)
    expect(ElNotification).toHaveBeenCalledTimes(1)

    mockWs.close()
    vi.advanceTimersByTime(35000)
    vi.advanceTimersByTime(35000)
    expect(ElNotification).toHaveBeenCalledTimes(1)
  })

  it('close without connect does not throw', () => {
    expect(() => mockWs.close()).not.toThrow()
  })

  it('reconnect after close works correctly', () => {
    mockWs.connect()
    vi.advanceTimersByTime(35000)
    expect(ElNotification).toHaveBeenCalledTimes(1)

    mockWs.close()
    vi.advanceTimersByTime(70000)
    expect(ElNotification).toHaveBeenCalledTimes(1)

    mockWs.connect()
    vi.advanceTimersByTime(35000)
    expect(ElNotification).toHaveBeenCalledTimes(2)
  })
})
