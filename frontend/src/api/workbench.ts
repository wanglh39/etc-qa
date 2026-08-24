import request from '@/utils/request'

export interface QueryRequest {
  question: string
  category_l1?: string
}

export interface CandidateResult {
  qa_id: number
  question: string
  answer: string
  category_l1?: string
  category_l2?: string
  internal_process?: string
  feedback_dept?: string
  score: number
}

export interface QueryResponse {
  query: string
  standardized_query: string
  confidence: string
  candidates: CandidateResult[]
  total_candidates: number
  work_order_id?: string
}

export function queryQA(params: QueryRequest): Promise<QueryResponse> {
  return request.post('/query', params).then((res) => res.data)
}

export function getAsrHealth(): Promise<{
  loaded: boolean
  model?: string
  device?: string
  finetuned?: boolean
}> {
  return request.get('/asr/health').then((res) => res.data)
}
