import { defineStore } from 'pinia'
export const useSessionStore = defineStore('session', {
  state: () => ({
    pendingTicketNum: 1, // 新咨询消息数量
    noticeList: [] as string[],
  }),
  actions: {
    updateNotice(msg: string) {
      this.noticeList.push(msg)
      this.pendingTicketNum = this.noticeList.length
    },
  },
})
