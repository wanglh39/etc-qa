import request from '@/utils/request'

// ===== 业务配置 =====

export function getConfig(key: string) {
  return request.get<{ key: string; value: any }>(`/config/${key}`).then((r) => r.data)
}

export function setConfig(key: string, value: any, description?: string) {
  return request.put(`/config/${key}`, { value, description }).then((r) => r.data)
}

export function reloadConfig() {
  return request.post('/config/reload').then((r) => r.data)
}

// ===== Prompt 管理 =====

export interface PromptKeySummary {
  prompt_key: string
  latest_version: number
  active_count: number
  shadow_count: number
}

export interface PromptVersionInfo {
  id?: number
  prompt_key: string
  version: number
  is_active: number
  status: string
  description: string
  created_at?: string
  template_text_preview: string
}

export function listPrompts() {
  return request.get<PromptKeySummary[]>('/prompts').then((r) => r.data)
}

export function listVersions(promptKey: string) {
  return request.get<PromptVersionInfo[]>(`/prompts/${promptKey}/versions`).then((r) => r.data)
}

export function getVersion(promptKey: string, version: number) {
  return request.get(`/prompts/${promptKey}/versions/${version}`).then((r) => r.data)
}

export function publishPrompt(promptKey: string, templateText: string, description?: string) {
  return request.post('/prompts/publish', { prompt_key: promptKey, template_text: templateText, description }).then((r) => r.data)
}

export function rollbackPrompt(promptKey: string, targetVersion?: number) {
  return request.post('/prompts/rollback', { prompt_key: promptKey, target_version: targetVersion }).then((r) => r.data)
}
