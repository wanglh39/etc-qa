import request from '@/utils/request'

export interface QAListItem {
  id: number
  question: string
  answer: string
  category_l1: string
  category_l2: string
  status: string
  created_at?: string
  updated_at?: string
}

export interface QAListResponse {
  items: QAListItem[]
  total: number
  page: number
  page_size: number
}

export interface QADetailResponse {
  id: number
  question: string
  answer: string
  category_l1: string
  category_l2: string
  internal_process: string
  feedback_dept: string
  status: string
  created_at?: string
  updated_at?: string
}

export interface AddQARequest {
  question: string
  answer: string
  category_l1?: string
  category_l2?: string
  internal_process?: string
  feedback_dept?: string
}

export interface QASearchRequest {
  keyword: string
  category_l1?: string
  status?: string
  page?: number
  page_size?: number
}

export function getQAList(params: {
  page?: number
  page_size?: number
  category_l1?: string
  status?: string
}) {
  return request.get<QAListResponse>('/qa/list', { params }).then((r) => r.data)
}

export function searchQA(data: QASearchRequest) {
  return request.post<QAListResponse>('/qa/search', data).then((r) => r.data)
}

export function getQADetail(qaId: number) {
  return request.get<QADetailResponse>(`/qa/${qaId}`).then((r) => r.data)
}

export function addQA(data: AddQARequest) {
  return request.post<{ qa_id: number; message: string }>('/add', data).then((r) => r.data)
}

export function updateQAStatus(qaId: number, status: string) {
  return request.put('/qa/status', { qa_id: qaId, status }).then((r) => r.data)
}

export function deleteQA(qaId: number) {
  return request.delete(`/qa/${qaId}`).then((r) => r.data)
}

export function getCategories() {
  return request.get<{ categories: any }>('/categories').then((r) => r.data)
}

export interface CategoryNode {
  id: number
  label: string
  parentId: number | null
  description?: string
  children?: CategoryNode[]
}

export interface CategoryPayload {
  label: string
  parent_id?: number | null
  description?: string
}

export function createCategory(data: CategoryPayload) {
  return request.post<{ id: number; message: string }>('/categories', data).then((r) => r.data)
}

export function updateCategory(id: number, data: CategoryPayload) {
  return request.put<{ id: number; message: string }>(`/categories/${id}`, data).then((r) => r.data)
}

export function deleteCategory(id: number) {
  return request.delete<{ id: number; message: string }>(`/categories/${id}`).then((r) => r.data)
}
