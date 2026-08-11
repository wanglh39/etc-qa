// 纯前端模拟websocket，无需真实ws服务
import { ElNotification } from 'element-plus'

class MockWebSocket {
  timer: ReturnType<typeof setInterval> | null
  constructor() {
    this.timer = null
  }
  connect() {
    // 每间隔35秒模拟推送一条新工单提醒
    this.timer = setInterval(() => {
      ElNotification({
        title: '新咨询消息',
        message: '收到用户新的智能问答工单，请前往工作台处理',
        type: 'info'
      })
    }, 35000)
  }
  close() {
    if (this.timer) clearInterval(this.timer)
  }
}
export const mockWs = new MockWebSocket()
