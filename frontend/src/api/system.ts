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
  permissions: string[]
  created_at?: string
}

export interface RoleCreateRequest {
  role_key: string
  role_name: string
  description?: string
  permissions?: string[]
}

export interface RoleUpdateRequest {
  role_name?: string
  description?: string
  permissions?: string[]
}

export function getRoleList() {
  return request.get<RoleItem[]>('/roles').then((r) => r.data)
}

export function getMyPermissions() {
  return request.get<{ permissions: string[] }>('/roles/permissions').then((r) => r.data.permissions)
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

// ===== 调度器管理 =====

export interface SchedulerJob {
  id: string
  next_run_time: string | null
  trigger: string
}

export interface SchedulerStatus {
  running: boolean
  jobs: SchedulerJob[]
  task_stats: Record<string, any>
}

export interface SchedulerLogItem {
  id: number
  task_name: string
  stats: string
  result: string
  created_at: string
}

export interface SchedulerLogResponse {
  items: SchedulerLogItem[]
  total: number
  page: number
  page_size: number
}

export function getSchedulerStatus() {
  return request.get<SchedulerStatus>('/scheduler/status').then((r) => r.data)
}

export function triggerSchedulerJob(jobId: string) {
  return request.post(`/scheduler/trigger/${jobId}`).then((r) => r.data)
}

export function updateSchedulerConfig(jobId: string, hours?: number, minutes?: number) {
  const params: Record<string, number | string> = { job_id: jobId }
  if (hours !== undefined) params.hours = hours
  if (minutes !== undefined) params.minutes = minutes
  return request.put('/scheduler/config', null, { params }).then((r) => r.data)
}

export function getSchedulerLogs(params: { page?: number; page_size?: number }) {
  return request.get<SchedulerLogResponse>('/scheduler/logs', { params }).then((r) => r.data)
}

export interface AlertEventItem {
  id: number
  rule_id: string
  severity: string
  message: string
  current_value: number
  threshold_value: number
  status: string
  acked_by: string | null
  acked_at: string | null
  created_at: string
}

export interface AlertListResponse {
  items: AlertEventItem[]
  total: number
  page: number
  page_size: number
}

export function getAlertList(params: { page?: number; page_size?: number; status?: string; severity?: string }) {
  return request.get<AlertListResponse>('/alerts', { params }).then((r) => r.data)
}

export function ackAlert(alertId: number) {
  return request.put(`/alerts/${alertId}/ack`).then((r) => r.data)
}

export function getAlertMetrics() {
  return request.get<Record<string, any>>('/alerts/metrics').then((r) => r.data)
}

// ===== 系统状态 =====

export interface SystemComponent {
  name: string
  status: string
  latency_ms: number
  detail: string
}

export interface SystemStatusResponse {
  overall: string
  components: SystemComponent[]
  timestamp: string
}

export function getSystemStatus() {
  return request.get<SystemStatusResponse>('/system/status').then((r) => r.data)
}

// ===== 系统日志 =====

export interface SystemLogItem {
  line: string
  level: string
}

export interface SystemLogResponse {
  logs: SystemLogItem[]
  total: number
}

export function getSystemLogs(params: { lines?: number; level?: string }) {
  return request.get<SystemLogResponse>('/system/logs', { params }).then((r) => r.data)
}

