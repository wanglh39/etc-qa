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

// ===== 账号管理 =====

export interface UserListItem {
  id: number
  username: string
  role: string
  dept: string
  status: string
  created_at?: string
  updated_at?: string
}

export interface UserListResponse {
  items: UserListItem[]
  total: number
  page: number
  page_size: number
}

export interface UserCreateRequest {
  username: string
  password: string
  role: string
  dept?: string
  status?: string
}

export interface UserUpdateRequest {
  role?: string
  dept?: string
  status?: string
}

export function getUserList(params: { page?: number; page_size?: number; role?: string; status?: string }) {
  return request.get<UserListResponse>('/users', { params }).then((r) => r.data)
}

export function createUser(data: UserCreateRequest) {
  return request.post('/users', data).then((r) => r.data)
}

export function updateUser(userId: number, data: UserUpdateRequest) {
  return request.put(`/users/${userId}`, data).then((r) => r.data)
}

export function resetPassword(userId: number, newPassword: string) {
  return request.put(`/users/${userId}/password`, { user_id: userId, new_password: newPassword }).then((r) => r.data)
}

export function deleteUser(userId: number) {
  return request.delete(`/users/${userId}`).then((r) => r.data)
}

// ===== 角色管理 =====

export interface RoleItem {
  id: number
  role_key: string
  role_name: string
  description: string
  created_at?: string
}

export interface RoleCreateRequest {
  role_key: string
  role_name: string
  description?: string
}

export interface RoleUpdateRequest {
  role_name?: string
  description?: string
}

export function getRoleList() {
  return request.get<RoleItem[]>('/roles').then((r) => r.data)
}

export function createRole(data: RoleCreateRequest) {
  return request.post('/roles', data).then((r) => r.data)
}

export function updateRole(roleId: number, data: RoleUpdateRequest) {
  return request.put(`/roles/${roleId}`, data).then((r) => r.data)
}

export function deleteRole(roleId: number) {
  return request.delete(`/roles/${roleId}`).then((r) => r.data)
}

// ===== 操作日志 =====

export interface OperationLogItem {
  id: number
  operator: string
  action: string
  target_type: string
  target_id: number | null
  detail: string
  ip: string
  created_at: string
}

export interface OperationLogListResponse {
  items: OperationLogItem[]
  total: number
  page: number
  page_size: number
}

export function getOperationList(params: { page?: number; page_size?: number; operator?: string; action?: string }) {
  return request.get<OperationLogListResponse>('/operations', { params }).then((r) => r.data)
}

