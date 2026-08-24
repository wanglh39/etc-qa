import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

vi.mock('vue-router', () => ({
  createRouter: vi.fn(() => ({ beforeEach: vi.fn() })),
  createWebHistory: vi.fn(),
}))

vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), warning: vi.fn(), error: vi.fn(), info: vi.fn() },
}))

let mockWsInstance: any = null

class MockWebSocket {
  static OPEN = 1
  static CLOSED = 3
  binaryType = ''
  readyState = MockWebSocket.OPEN
  onopen: ((ev: any) => void) | null = null
  onmessage: ((ev: any) => void) | null = null
  onerror: ((ev: any) => void) | null = null
  onclose: ((ev: any) => void) | null = null
  send = vi.fn()
  close = vi.fn()
  constructor(public url: string) {
    mockWsInstance = this
  }
}

beforeEach(() => {
  setActivePinia(createPinia())
  mockWsInstance = null
  Object.defineProperty(window, 'isSecureContext', { value: true, configurable: true })
  Object.defineProperty(window, 'location', {
    value: { hostname: 'localhost', host: 'localhost' },
    configurable: true,
  })
  vi.stubGlobal('WebSocket', MockWebSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
})

import { useStreamingASR } from '@/composables/useStreamingASR'

describe('useStreamingASR initial state', () => {
  it('returns correct initial state', () => {
    const asr = useStreamingASR()
    expect(asr.isRecording.value).toBe(false)
    expect(asr.isConnected.value).toBe(false)
    expect(asr.partialText.value).toBe('')
    expect(asr.fullText.value).toBe('')
    expect(asr.queryResult.value).toBeNull()
    expect(asr.asrState.value).toBe('IDLE')
    expect(asr.errorMsg.value).toBe('')
  })

  it('returns all expected methods', () => {
    const asr = useStreamingASR()
    expect(typeof asr.connect).toBe('function')
    expect(typeof asr.disconnect).toBe('function')
    expect(typeof asr.startRecording).toBe('function')
    expect(typeof asr.stopRecording).toBe('function')
    expect(typeof asr.reset).toBe('function')
    expect(typeof asr.selectAnswer).toBe('function')
  })
})

describe('useStreamingASR connect', () => {
  it('connects to WebSocket and sets isConnected on open', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    expect(mockWsInstance).toBeTruthy()
    expect(mockWsInstance.url).toBe('ws://localhost/ws/asr/stream')
    mockWsInstance.onopen({})
    await promise
    expect(asr.isConnected.value).toBe(true)
    expect(asr.errorMsg.value).toBe('')
  })

  it('rejects on WebSocket error', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onerror({})
    await expect(promise).rejects.toThrow('WebSocket连接错误')
    expect(asr.isConnected.value).toBe(false)
    expect(asr.errorMsg.value).toBe('WebSocket连接错误')
  })

  it('sets isConnected false on close', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    expect(asr.isConnected.value).toBe(true)
    mockWsInstance.onclose({})
    expect(asr.isConnected.value).toBe(false)
    expect(asr.isRecording.value).toBe(false)
  })

  it('sets binaryType to arraybuffer', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    expect(mockWsInstance.binaryType).toBe('arraybuffer')
  })
})

describe('useStreamingASR handleMessage', () => {
  it('handles ready message', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({ data: JSON.stringify({ type: 'ready', state: 'READY' }) })
    expect(asr.asrState.value).toBe('READY')
  })

  it('handles ready message with default state', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({ data: JSON.stringify({ type: 'ready' }) })
    expect(asr.asrState.value).toBe('IDLE')
  })

  it('handles state_change message', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({ data: JSON.stringify({ type: 'state_change', state: 'LISTENING' }) })
    expect(asr.asrState.value).toBe('LISTENING')
  })

  it('handles partial message', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({ data: JSON.stringify({ type: 'partial', text: '你好' }) })
    expect(asr.partialText.value).toBe('你好')
  })

  it('handles partial message with empty text', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({ data: JSON.stringify({ type: 'partial' }) })
    expect(asr.partialText.value).toBe('')
  })

  it('handles final message', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    asr.partialText.value = 'partial text'
    mockWsInstance.onmessage({ data: JSON.stringify({ type: 'final', full_text: '最终结果' }) })
    expect(asr.fullText.value).toBe('最终结果')
    expect(asr.partialText.value).toBe('')
  })

  it('handles query_result message', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({
      data: JSON.stringify({
        type: 'query_result',
        query_text: '怎么退费',
        data: {
          candidates: [{ qa_id: 1, question: 'q', answer: 'a', score: 0.9 }],
          confidence: 'high',
          standardized_query: '退费流程',
        },
      }),
    })
    expect(asr.queryResult.value).toBeTruthy()
    expect(asr.queryResult.value!.query_text).toBe('怎么退费')
    expect(asr.queryResult.value!.confidence).toBe('high')
    expect(asr.queryResult.value!.standardized_query).toBe('退费流程')
    expect(asr.queryResult.value!.candidates).toHaveLength(1)
  })

  it('handles query_result with fallback query field', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({
      data: JSON.stringify({
        type: 'query_result',
        query_text: 'test',
        data: { candidates: [], confidence: 'low', query: 'fallback' },
      }),
    })
    expect(asr.queryResult.value!.standardized_query).toBe('fallback')
  })

  it('handles filtered message with greeting reason', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({ data: JSON.stringify({ type: 'filtered', reason: 'greeting' }) })
    expect(asr.asrState.value).toBe('IDLE')
  })

  it('handles filtered message with too_short reason', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({ data: JSON.stringify({ type: 'filtered', reason: 'too_short' }) })
    expect(asr.asrState.value).toBe('IDLE')
  })

  it('handles error message', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({ data: JSON.stringify({ type: 'error', message: 'ASR模型未加载' }) })
    expect(asr.errorMsg.value).toBe('ASR模型未加载')
  })

  it('handles error message with default', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({ data: JSON.stringify({ type: 'error' }) })
    expect(asr.errorMsg.value).toBe('未知错误')
  })

  it('ignores non-JSON messages', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    mockWsInstance.onmessage({ data: 'not json' })
    expect(asr.errorMsg.value).toBe('')
  })
})

describe('useStreamingASR sendControl', () => {
  it('sends control message when connected', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    asr.reset()
    expect(mockWsInstance.send).toHaveBeenCalledWith(JSON.stringify({ type: 'reset' }))
  })

  it('selectAnswer sends select_answer with qaId', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    asr.selectAnswer(42)
    expect(mockWsInstance.send).toHaveBeenCalledWith(
      JSON.stringify({ type: 'select_answer', qa_id: 42 })
    )
  })

  it('does not send when WebSocket not open', () => {
    const asr = useStreamingASR()
    asr.selectAnswer(1)
    expect(mockWsInstance).toBeNull()
  })
})

describe('useStreamingASR reset', () => {
  it('clears all text state and sends reset control', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    asr.partialText.value = 'partial'
    asr.fullText.value = 'full'
    asr.queryResult.value = { query_text: 'q', candidates: [], confidence: 'high' }
    asr.asrState.value = 'LISTENING'
    asr.reset()
    expect(asr.partialText.value).toBe('')
    expect(asr.fullText.value).toBe('')
    expect(asr.queryResult.value).toBeNull()
    expect(asr.asrState.value).toBe('IDLE')
  })
})

describe('useStreamingASR stopRecording', () => {
  it('sets isRecording to false', () => {
    const asr = useStreamingASR()
    asr.isRecording.value = true
    asr.stopRecording()
    expect(asr.isRecording.value).toBe(false)
  })
})

describe('useStreamingASR disconnect', () => {
  it('stops recording and closes WebSocket', async () => {
    const asr = useStreamingASR()
    const promise = asr.connect()
    mockWsInstance.onopen({})
    await promise
    asr.isRecording.value = true
    asr.disconnect()
    expect(asr.isRecording.value).toBe(false)
    expect(asr.isConnected.value).toBe(false)
    expect(mockWsInstance.close).toHaveBeenCalled()
  })

  it('works without prior connection', () => {
    const asr = useStreamingASR()
    asr.disconnect()
    expect(asr.isConnected.value).toBe(false)
  })
})

describe('useStreamingASR startRecording errors', () => {
  it('throws on non-secure context', async () => {
    Object.defineProperty(window, 'isSecureContext', { value: false, configurable: true })
    Object.defineProperty(window, 'location', {
      value: { hostname: 'example.com', host: 'example.com' },
      configurable: true,
    })
    const asr = useStreamingASR()
    await expect(asr.startRecording()).rejects.toThrow('非安全上下文')
  })

  it('throws when mediaDevices unavailable', async () => {
    Object.defineProperty(navigator, 'mediaDevices', { value: undefined, configurable: true })
    const asr = useStreamingASR()
    await expect(asr.startRecording()).rejects.toThrow('不支持麦克风')
  })
})
