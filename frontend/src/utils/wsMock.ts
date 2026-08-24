// src/utils/wsMock.ts
import type { SessionRow } from '@/mock/workbench'
import { newMockSession } from '@/mock/workbench'

type CallBack = (item: SessionRow) => void
let timer: ReturnType<typeof setTimeout> | null = null

//开启模拟推送，延迟触发新会话下发
export const startMockWsPush = (callback: CallBack) => {
  timer = window.setTimeout(() => {
    callback(newMockSession)
  }, 30 * 1000) // 30秒推送一条新会话，可自行修改时长
}

//关闭定时器
export const stopMockWsPush = () => {
  if (timer) {
    clearTimeout(timer)
    timer = null // 清空引用，防止重复清理
  }
}
