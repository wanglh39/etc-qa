import request from '@/utils/request'

export interface WorkOrderListItem {
  id: number
  external_id: string
  raw_data: string
  status: string
  created_at?: string
  updated_at?: string
}

export interface WorkOrderListResponse {
  items: WorkOrderListItem[]
  total: number
  page: number
  page_size: number
}

export interface AgentProcessRequest {
  question: string
  answer?: string
  context?: string
  user_id?: string
}

export interface AgentProcessResponse {
  question: string
  answer: string
  internal_process: string
  feedback_dept: string
  is_duplicate: boolean
  duplicate_of?: number
  similarity_score: number
  category_l1: string
  category_l2: string
  category_confidence: number
  needs_review: boolean
  review_highlights: string[]
  current_step: string
  error?: string
}

export function getWorkOrders(params: {
  page?: number
  page_size?: number
  status?: string
  dept?: string
}) {
  return request.get<WorkOrderListResponse>('/work_orders', { params }).then((r) => r.data)
}

export interface WorkOrderStats {
  total: number
  submitted: number
  answered: number
  processed: number
  today?: number
}

export function getWorkOrderStats() {
  return request.get<WorkOrderStats>('/work_orders/stats').then((r) => r.data)
}

export function processAgent(data: AgentProcessRequest) {
  return request.post<AgentProcessResponse>('/agent/process', data).then((r) => r.data)
}

export interface AuditLogItem {
  id: number
  qa_id?: number
  question: string
  answer: string
  result: string
  operator: string
  created_at?: string
}

export interface AuditLogListResponse {
  items: AuditLogItem[]
  total: number
  page: number
  page_size: number
}

export function getAuditHistory(params: { page?: number; page_size?: number }) {
  return request.get<AuditLogListResponse>('/audit/history', { params }).then((r) => r.data)
}
