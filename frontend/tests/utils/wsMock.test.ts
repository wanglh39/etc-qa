import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

describe('utils/wsMock', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('startMockWsPush calls callback with newMockSession after 30s', async () => {
    const { startMockWsPush, stopMockWsPush } = await import('@/utils/wsMock')
    const { newMockSession } = await import('@/mock/workbench')
    const cb = vi.fn()
    startMockWsPush(cb)
    expect(cb).not.toHaveBeenCalled()
    vi.advanceTimersByTime(30000)
    expect(cb).toHaveBeenCalledTimes(1)
    expect(cb).toHaveBeenCalledWith(newMockSession)
    stopMockWsPush()
  })

  it('stopMockWsPush prevents callback from firing', async () => {
    const { startMockWsPush, stopMockWsPush } = await import('@/utils/wsMock')
    const cb = vi.fn()
    startMockWsPush(cb)
    stopMockWsPush()
    vi.advanceTimersByTime(60000)
    expect(cb).not.toHaveBeenCalled()
  })

  it('stopMockWsPush without start does not throw', async () => {
    const { stopMockWsPush } = await import('@/utils/wsMock')
    expect(() => stopMockWsPush()).not.toThrow()
  })
})
