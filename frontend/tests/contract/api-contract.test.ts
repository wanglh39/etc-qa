import { describe, it, expect } from 'vitest'
import schema from './openapi.json'

type Method = 'get' | 'post' | 'put' | 'delete'

const frontendApiCalls: { method: Method; path: string; file: string }[] = [
  { method: 'post', path: '/api/auth/login', file: 'api/auth.ts' },
  { method: 'get', path: '/api/auth/verify', file: 'api/auth.ts' },
  { method: 'post', path: '/api/auth/impersonate', file: 'api/auth.ts' },
  { method: 'post', path: '/api/query', file: 'api/workbench.ts' },
  { method: 'get', path: '/api/asr/health', file: 'api/workbench.ts' },
  { method: 'get', path: '/api/stats', file: 'api/dashboard.ts' },
  { method: 'get', path: '/api/stats/trend', file: 'api/dashboard.ts' },
  { method: 'get', path: '/api/work_orders', file: 'api/audit.ts' },
  { method: 'get', path: '/api/work_orders/stats', file: 'api/audit.ts' },
  { method: 'post', path: '/api/agent/process', file: 'api/audit.ts' },
  { method: 'get', path: '/api/audit/history', file: 'api/audit.ts' },
  { method: 'post', path: '/api/work_orders', file: 'api/workorder.ts' },
  { method: 'get', path: '/api/work_orders/{id}', file: 'api/workorder.ts' },
  { method: 'put', path: '/api/work_orders/{id}/reply', file: 'api/workorder.ts' },
  { method: 'get', path: '/api/qa/list', file: 'api/knowledge.ts' },
  { method: 'post', path: '/api/qa/search', file: 'api/knowledge.ts' },
  { method: 'get', path: '/api/qa/{qaId}', file: 'api/knowledge.ts' },
  { method: 'post', path: '/api/add', file: 'api/knowledge.ts' },
  { method: 'put', path: '/api/qa/status', file: 'api/knowledge.ts' },
  { method: 'delete', path: '/api/qa/{qaId}', file: 'api/knowledge.ts' },
  { method: 'get', path: '/api/categories', file: 'api/knowledge.ts' },
  { method: 'post', path: '/api/categories', file: 'api/knowledge.ts' },
  { method: 'put', path: '/api/categories/{id}', file: 'api/knowledge.ts' },
  { method: 'delete', path: '/api/categories/{id}', file: 'api/knowledge.ts' },
  { method: 'get', path: '/api/config/{key}', file: 'api/system.ts' },
  { method: 'put', path: '/api/config/{key}', file: 'api/system.ts' },
  { method: 'post', path: '/api/config/reload', file: 'api/system.ts' },
  { method: 'get', path: '/api/users', file: 'api/system.ts' },
  { method: 'post', path: '/api/users', file: 'api/system.ts' },
  { method: 'put', path: '/api/users/{userId}', file: 'api/system.ts' },
  { method: 'delete', path: '/api/users/{userId}', file: 'api/system.ts' },
  { method: 'get', path: '/api/roles', file: 'api/system.ts' },
  { method: 'post', path: '/api/roles', file: 'api/system.ts' },
  { method: 'put', path: '/api/roles/{roleId}', file: 'api/system.ts' },
  { method: 'delete', path: '/api/roles/{roleId}', file: 'api/system.ts' },
  { method: 'get', path: '/api/operations', file: 'api/system.ts' },
  { method: 'get', path: '/api/scheduler/status', file: 'api/system.ts' },
  { method: 'post', path: '/api/scheduler/trigger/{jobId}', file: 'api/system.ts' },
  { method: 'put', path: '/api/scheduler/config', file: 'api/system.ts' },
  { method: 'get', path: '/api/scheduler/logs', file: 'api/system.ts' },
  { method: 'get', path: '/api/alerts', file: 'api/system.ts' },
  { method: 'put', path: '/api/alerts/{alertId}/ack', file: 'api/system.ts' },
  { method: 'get', path: '/api/alerts/metrics', file: 'api/system.ts' },
  { method: 'get', path: '/api/system/status', file: 'api/system.ts' },
  { method: 'get', path: '/api/system/logs', file: 'api/system.ts' },
]

function normalizePath(path: string): string {
  return path.replace(/\{[^}]+\}/g, '{param}')
}

function findInSchema(method: string, path: string): boolean {
  const normalized = normalizePath(path)
  for (const schemaPath of Object.keys(schema.paths)) {
    const schemaNormalized = schemaPath.replace(/\{[^}]+\}/g, '{param}')
    if (schemaNormalized === normalized) {
      return !!(schema.paths as any)[schemaPath][method]
    }
  }
  return false
}

describe('前后端 API 契约测试', () => {
  it('前端所有 API 调用在后端 schema 中存在', () => {
    const missing: string[] = []
    for (const call of frontendApiCalls) {
      if (!findInSchema(call.method, call.path)) {
        missing.push(`${call.method.toUpperCase()} ${call.path} (${call.file})`)
      }
    }
    expect(missing, `后端缺失的端点:\n${missing.join('\n')}`).toEqual([])
  })

  it('前端 API 调用无重复', () => {
    const seen = new Set<string>()
    const duplicates: string[] = []
    for (const call of frontendApiCalls) {
      const key = `${call.method} ${normalizePath(call.path)}`
      if (seen.has(key)) duplicates.push(key)
      seen.add(key)
    }
    expect(duplicates, `重复的 API 调用:\n${duplicates.join('\n')}`).toEqual([])
  })

  it('后端 schema 端点数量合理', () => {
    const pathCount = Object.keys(schema.paths).length
    expect(pathCount).toBeGreaterThanOrEqual(40)
    expect(pathCount).toBeLessThanOrEqual(60)
  })
})
