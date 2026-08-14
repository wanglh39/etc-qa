import request from '@/utils/request'

export interface WorkOrderCreateParams {
  service_id: string
  customer_name: string
  phone: string
  problem_type: string
  next_dept: string
  priority: string
  detail_desc: string
}

export interface WorkOrderDetail {
  id: number
  external_id: string
  status: string
  dept: string
  service_id: string
  customer_name: string
  phone: string
  problem_type: string
  next_dept: string
  priority: string
  detail_desc: string
  handle_remark: string
  created_at?: string
  updated_at?: string
}

export interface WorkOrderReplyParams {
  handle_remark: string
}

export function createWorkOrder(data: WorkOrderCreateParams) {
  return request.post<WorkOrderDetail>('/work_orders', data).then((r) => r.data)
}

export function getWorkOrderDetail(id: number | string) {
  return request.get<WorkOrderDetail>(`/work_orders/${id}`).then((r) => r.data)
}

export function replyWorkOrder(id: number | string, data: WorkOrderReplyParams) {
  return request.put<WorkOrderDetail>(`/work_orders/${id}/reply`, data).then((r) => r.data)
}
