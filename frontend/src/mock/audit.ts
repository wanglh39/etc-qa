// 待审核知识
export interface AuditRow {
  id: string
  question: string
  draftAnswer: string
  categoryName: string
  confidence: number // 置信度 0-100
  createTime: string
}
export const waitAuditList: AuditRow[] = [
  {
    id: "A001",
    question: "后台导出报表空白",
    draftAnswer: "检查导出筛选时间范围，切换浏览器重试",
    categoryName: "系统功能类",
    confidence: 62,
    createTime: "2026-07-11 09:10"
  },
  {
    id: "A002",
    question: "会员权益无法领取",
    draftAnswer: "确认账号完成实名认证，权益发放延迟10分钟内到账",
    categoryName: "会员问题",
    confidence: 91,
    createTime: "2026-07-11 09:30"
  }
]

// 审核历史记录
export interface AuditRecord {
  id: string
  question: string
  result: 'pass' | 'reject'
  auditTime: string
  auditor: string
}
export const auditRecordList: AuditRecord[] = [
  { id: "R001", question: "验证码收不到", result: "pass", auditTime: "2026-07-10 14:20", auditor: "管理员" },
  { id: "R002", question: "优惠券过期", result: "reject", auditTime: "2026-07-10 15:10", auditor: "管理员" }
]