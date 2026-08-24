export interface SessionRow {
  userId: string
  problemAbstract: string
  accessTime: string
  audioSrc: string
  voiceText: string
  ragReply: string
  status: 'normal' | 'invalid'
}
//模拟两条会话数据，对应截图表格U0001、U0002
export const sessionList: SessionRow[] = [
  {
    userId: 'U0001',
    problemAbstract: '账号无法登录',
    accessTime: '2026-07-10 08:45',
    audioSrc: '/mock-audio/u0001.mp3',
    voiceText: '我输入账号密码一直验证失败，无法正常登录后台平台',
    ragReply: '建议清除浏览器缓存之后重置密码，重试仍然失败可以提交CRN工单核验账号风控状态',
    status: 'normal',
  },
  {
    userId: 'U0002',
    problemAbstract: '订单重复扣款',
    accessTime: '2026-07-10 09:12',
    audioSrc: '/mock-audio/u0002.mp3',
    voiceText: '下单付款时银行卡扣款两次，想要申请退回重复的钱款',
    ragReply: '系统通常会在1-3个工作日原路退回重复扣款，着急的话可以上传扣款凭证加急审核',
    status: 'normal',
  },
]
//模拟websocket后续新增会话
export const newMockSession: SessionRow = {
  userId: 'U0003',
  problemAbstract: '知识库检索不到内容',
  accessTime: '2026-07-11 10:00',
  audioSrc: '/mock-audio/u0003.mp3',
  voiceText: '我搜索常见问题找不到对应的知识库解答',
  ragReply: '可以更换关键词进行检索，也可以前往分类管理查看分类层级是否正确',
  status: 'normal',
}
