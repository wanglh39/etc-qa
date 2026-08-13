import request from '@/utils/request'

export interface StatsResponse {
  qa_total: number
  qa_active: number
  qa_deprecated: number
  qa_archived: number
  work_order_total: number
  work_order_submitted: number
  work_order_processed: number
  category_stats: Record<string, number>
}

export function getStats() {
  return request.get<StatsResponse>('/stats').then((r) => r.data)
}

export interface TrendResponse {
  dates: string[]
  counts: number[]
}

export function getStatsTrend(days?: number) {
  return request.get<TrendResponse>('/stats/trend', { params: { days } }).then((r) => r.data)
}
