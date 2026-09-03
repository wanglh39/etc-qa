import { ref, onUnmounted } from 'vue'

export interface ASRCandidate {
  qa_id: number
  question: string
  answer: string
  score: number
  category_l1?: string
  category_l2?: string
}

export interface ASRQueryResult {
  query_text: string
  candidates: ASRCandidate[]
  confidence: string
  standardized_query?: string
}

export function useStreamingASR() {
  const isRecording = ref(false)
  const isConnected = ref(false)
  const partialText = ref('')
  const fullText = ref('')
  const queryResult = ref<ASRQueryResult | null>(null)
  const asrState = ref('IDLE')
  const errorMsg = ref('')

  let ws: WebSocket | null = null
  let audioContext: AudioContext | null = null
  let mediaStream: MediaStream | null = null
  let scriptNode: ScriptProcessorNode | null = null
  let sourceNode: MediaStreamAudioSourceNode | null = null

  const TARGET_SAMPLE_RATE = 16000

  const connect = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws'
      const wsUrl = `${protocol}://${window.location.host}/ws/asr/stream`
      ws = new WebSocket(wsUrl)
      ws.binaryType = 'arraybuffer'

      ws.onopen = () => {
        isConnected.value = true
        errorMsg.value = ''
        resolve()
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          handleMessage(msg)
        } catch {
          // ignore non-json
        }
      }

      ws.onerror = () => {
        errorMsg.value = 'WebSocket连接错误'
        isConnected.value = false
        reject(new Error('WebSocket连接错误'))
      }

      ws.onclose = () => {
        isConnected.value = false
        isRecording.value = false
      }
    })
  }

  const handleMessage = (msg: any) => {
    switch (msg.type) {
      case 'ready':
        asrState.value = msg.state || 'IDLE'
        break
      case 'state_change':
        asrState.value = msg.state
        break
      case 'partial':
        partialText.value = msg.text || ''
        break
      case 'final':
        fullText.value = msg.full_text || ''
        partialText.value = ''
        break
      case 'query_result':
        queryResult.value = {
          query_text: msg.query_text || '',
          candidates: msg.data?.candidates || [],
          confidence: msg.data?.confidence || 'none',
          standardized_query: msg.data?.standardized_query || msg.data?.query || '',
        }
        break
      case 'filtered':
        if (msg.reason === 'greeting' || msg.reason === 'too_short') {
          break
        }
        break
      case 'error':
        errorMsg.value = msg.message || '未知错误'
        break
    }
  }

  const float32ToInt16 = (float32Array: Float32Array): Int16Array => {
    const int16Array = new Int16Array(float32Array.length)
    for (let i = 0; i < float32Array.length; i++) {
      const s = Math.max(-1, Math.min(1, float32Array[i]))
      int16Array[i] = s < 0 ? s * 0x8000 : s * 0x7fff
    }
    return int16Array
  }

  const downsampleBuffer = (buffer: Float32Array, sampleRate: number): Float32Array => {
    if (sampleRate === TARGET_SAMPLE_RATE) {
      return buffer
    }
    const ratio = sampleRate / TARGET_SAMPLE_RATE
    const newLength = Math.round(buffer.length / ratio)
    const result = new Float32Array(newLength)
    let offsetResult = 0
    let offsetBuffer = 0
    while (offsetResult < newLength) {
      const nextOffsetBuffer = Math.round((offsetResult + 1) * ratio)
      let accum = 0
      let count = 0
      for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
        accum += buffer[i]
        count++
      }
      result[offsetResult] = count > 0 ? accum / count : 0
      offsetResult++
      offsetBuffer = nextOffsetBuffer
    }
    return result
  }

  const startRecording = async () => {
    if (
      !window.isSecureContext &&
      window.location.hostname !== 'localhost' &&
      window.location.hostname !== '127.0.0.1'
    ) {
      throw new Error(
        '当前为非安全上下文（HTTP），浏览器禁止访问麦克风。请使用 localhost 或 HTTPS 访问'
      )
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error('浏览器不支持麦克风采集（navigator.mediaDevices 不可用）')
    }

    if (!ws || ws.readyState !== WebSocket.OPEN) {
      await connect()
    }

    try {
      mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 48000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })

      audioContext = new AudioContext({ sampleRate: 48000 })
      sourceNode = audioContext.createMediaStreamSource(mediaStream)

      const bufferSize = 4096
      scriptNode = audioContext.createScriptProcessor(bufferSize, 1, 1)

      scriptNode.onaudioprocess = (audioProcessingEvent) => {
        if (!ws || ws.readyState !== WebSocket.OPEN) return
        const inputBuffer = audioProcessingEvent.inputBuffer
        const channelData = inputBuffer.getChannelData(0)

        const downsampled = downsampleBuffer(channelData, audioContext!.sampleRate)
        const int16Data = float32ToInt16(downsampled)
        ws.send(int16Data.buffer as ArrayBuffer)
      }

      sourceNode.connect(scriptNode)
      scriptNode.connect(audioContext.destination)

      isRecording.value = true
      errorMsg.value = ''
    } catch (e: any) {
      errorMsg.value = `麦克风启动失败: ${e.message || e}`
      stopRecording()
      throw e
    }
  }

  const stopRecording = () => {
    isRecording.value = false

    if (scriptNode) {
      scriptNode.disconnect()
      scriptNode = null
    }
    if (sourceNode) {
      sourceNode.disconnect()
      sourceNode = null
    }
    if (mediaStream) {
      mediaStream.getTracks().forEach((t) => t.stop())
      mediaStream = null
    }
    if (audioContext) {
      audioContext.close()
      audioContext = null
    }
  }

  const disconnect = () => {
    stopRecording()
    if (ws) {
      ws.close()
      ws = null
    }
    isConnected.value = false
  }

  const sendControl = (msg: object) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(msg))
    }
  }

  const reset = () => {
    sendControl({ type: 'reset' })
    partialText.value = ''
    fullText.value = ''
    queryResult.value = null
    asrState.value = 'IDLE'
  }

  const selectAnswer = (qaId: number) => {
    sendControl({ type: 'select_answer', qa_id: qaId })
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    isRecording,
    isConnected,
    partialText,
    fullText,
    queryResult,
    asrState,
    errorMsg,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    reset,
    selectAnswer,
  }
}
