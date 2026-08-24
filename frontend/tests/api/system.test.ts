import { describe, it, expect, vi, beforeEach } from 'vitest'
import request from '@/utils/request'
import {
  getConfig,
  setConfig,
  reloadConfig,
  getUserList,
  createUser,
  updateUser,
  resetPassword,
  deleteUser,
  getRoleList,
  getMyPermissions,
  createRole,
  updateRole,
  deleteRole,
  getOperationList,
  getSchedulerStatus,
  triggerSchedulerJob,
  updateSchedulerConfig,
  getSchedulerLogs,
  getAlertList,
  ackAlert,
  getAlertMetrics,
  getSystemStatus,
  getSystemLogs,
} from '@/api/system'

vi.mock('@/utils/request')

const mockedRequest = vi.mocked(request, true)

beforeEach(() => {
  vi.clearAllMocks()
})

describe('api/system', () => {
  describe('业务配置', () => {
    it('getConfig GETs /config/:key', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: { key: 'k', value: 'v' } })
      await getConfig('k')
      expect(mockedRequest.get).toHaveBeenCalledWith('/config/k')
    })

    it('setConfig PUTs value to /config/:key', async () => {
      mockedRequest.put.mockResolvedValueOnce({ data: {} })
      await setConfig('k', 'v', 'desc')
      expect(mockedRequest.put).toHaveBeenCalledWith('/config/k', {
        value: 'v',
        description: 'desc',
      })
    })

    it('setConfig omits description when not provided', async () => {
      mockedRequest.put.mockResolvedValueOnce({ data: {} })
      await setConfig('k', 'v')
      expect(mockedRequest.put).toHaveBeenCalledWith('/config/k', {
        value: 'v',
        description: undefined,
      })
    })

    it('reloadConfig POSTs to /config/reload', async () => {
      mockedRequest.post.mockResolvedValueOnce({ data: {} })
      await reloadConfig()
      expect(mockedRequest.post).toHaveBeenCalledWith('/config/reload')
    })
  })

  describe('账号管理', () => {
    it('getUserList GETs /users with params', async () => {
      mockedRequest.get.mockResolvedValueOnce({
        data: { items: [], total: 0, page: 1, page_size: 20 },
      })
      await getUserList({ page: 1, role: 'admin' })
      expect(mockedRequest.get).toHaveBeenCalledWith('/users', {
        params: { page: 1, role: 'admin' },
      })
    })

    it('createUser POSTs to /users', async () => {
      mockedRequest.post.mockResolvedValueOnce({ data: {} })
      await createUser({ username: 'u', password: 'p', role: 'admin' })
      expect(mockedRequest.post).toHaveBeenCalledWith('/users', {
        username: 'u',
        password: 'p',
        role: 'admin',
      })
    })

    it('updateUser PUTs to /users/:id', async () => {
      mockedRequest.put.mockResolvedValueOnce({ data: {} })
      await updateUser(5, { role: 'ops' })
      expect(mockedRequest.put).toHaveBeenCalledWith('/users/5', { role: 'ops' })
    })

    it('resetPassword PUTs to /users/:id/password', async () => {
      mockedRequest.put.mockResolvedValueOnce({ data: {} })
      await resetPassword(5, 'newpass')
      expect(mockedRequest.put).toHaveBeenCalledWith('/users/5/password', {
        user_id: 5,
        new_password: 'newpass',
      })
    })

    it('deleteUser DELETEs /users/:id', async () => {
      mockedRequest.delete.mockResolvedValueOnce({ data: {} })
      await deleteUser(5)
      expect(mockedRequest.delete).toHaveBeenCalledWith('/users/5')
    })
  })

  describe('角色管理', () => {
    it('getRoleList GETs /roles', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: [] })
      await getRoleList()
      expect(mockedRequest.get).toHaveBeenCalledWith('/roles')
    })

    it('getMyPermissions GETs /roles/permissions and unwraps .permissions', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: { permissions: ['read', 'write'] } })
      const result = await getMyPermissions()
      expect(mockedRequest.get).toHaveBeenCalledWith('/roles/permissions')
      expect(result).toEqual(['read', 'write'])
    })

    it('createRole POSTs to /roles', async () => {
      mockedRequest.post.mockResolvedValueOnce({ data: {} })
      await createRole({ role_key: 'x', role_name: 'X' })
      expect(mockedRequest.post).toHaveBeenCalledWith('/roles', { role_key: 'x', role_name: 'X' })
    })

    it('updateRole PUTs to /roles/:id', async () => {
      mockedRequest.put.mockResolvedValueOnce({ data: {} })
      await updateRole(3, { role_name: 'Y' })
      expect(mockedRequest.put).toHaveBeenCalledWith('/roles/3', { role_name: 'Y' })
    })

    it('deleteRole DELETEs /roles/:id', async () => {
      mockedRequest.delete.mockResolvedValueOnce({ data: {} })
      await deleteRole(3)
      expect(mockedRequest.delete).toHaveBeenCalledWith('/roles/3')
    })
  })

  describe('操作日志', () => {
    it('getOperationList GETs /operations with params', async () => {
      mockedRequest.get.mockResolvedValueOnce({
        data: { items: [], total: 0, page: 1, page_size: 20 },
      })
      await getOperationList({ operator: 'admin' })
      expect(mockedRequest.get).toHaveBeenCalledWith('/operations', {
        params: { operator: 'admin' },
      })
    })
  })

  describe('调度器管理', () => {
    it('getSchedulerStatus GETs /scheduler/status', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: { running: true, jobs: [], task_stats: {} } })
      await getSchedulerStatus()
      expect(mockedRequest.get).toHaveBeenCalledWith('/scheduler/status')
    })

    it('triggerSchedulerJob POSTs to /scheduler/trigger/:id', async () => {
      mockedRequest.post.mockResolvedValueOnce({ data: {} })
      await triggerSchedulerJob('daily_sync')
      expect(mockedRequest.post).toHaveBeenCalledWith('/scheduler/trigger/daily_sync')
    })

    it('updateSchedulerConfig PUTs with hours and minutes', async () => {
      mockedRequest.put.mockResolvedValueOnce({ data: {} })
      await updateSchedulerConfig('job1', 2, 30)
      expect(mockedRequest.put).toHaveBeenCalledWith('/scheduler/config', null, {
        params: { job_id: 'job1', hours: 2, minutes: 30 },
      })
    })

    it('updateSchedulerConfig PUTs with only job_id', async () => {
      mockedRequest.put.mockResolvedValueOnce({ data: {} })
      await updateSchedulerConfig('job1')
      expect(mockedRequest.put).toHaveBeenCalledWith('/scheduler/config', null, {
        params: { job_id: 'job1' },
      })
    })

    it('getSchedulerLogs GETs /scheduler/logs', async () => {
      mockedRequest.get.mockResolvedValueOnce({
        data: { items: [], total: 0, page: 1, page_size: 20 },
      })
      await getSchedulerLogs({ page: 1 })
      expect(mockedRequest.get).toHaveBeenCalledWith('/scheduler/logs', { params: { page: 1 } })
    })
  })

  describe('告警管理', () => {
    it('getAlertList GETs /alerts with params', async () => {
      mockedRequest.get.mockResolvedValueOnce({
        data: { items: [], total: 0, page: 1, page_size: 20 },
      })
      await getAlertList({ status: 'open', severity: 'critical' })
      expect(mockedRequest.get).toHaveBeenCalledWith('/alerts', {
        params: { status: 'open', severity: 'critical' },
      })
    })

    it('ackAlert PUTs to /alerts/:id/ack', async () => {
      mockedRequest.put.mockResolvedValueOnce({ data: {} })
      await ackAlert(99)
      expect(mockedRequest.put).toHaveBeenCalledWith('/alerts/99/ack')
    })

    it('getAlertMetrics GETs /alerts/metrics', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: { cpu: 50 } })
      await getAlertMetrics()
      expect(mockedRequest.get).toHaveBeenCalledWith('/alerts/metrics')
    })
  })

  describe('系统状态', () => {
    it('getSystemStatus GETs /system/status', async () => {
      mockedRequest.get.mockResolvedValueOnce({
        data: { overall: 'ok', components: [], timestamp: '' },
      })
      await getSystemStatus()
      expect(mockedRequest.get).toHaveBeenCalledWith('/system/status')
    })
  })

  describe('系统日志', () => {
    it('getSystemLogs GETs /system/logs with params', async () => {
      mockedRequest.get.mockResolvedValueOnce({ data: { logs: [], total: 0 } })
      await getSystemLogs({ lines: 100, level: 'ERROR' })
      expect(mockedRequest.get).toHaveBeenCalledWith('/system/logs', {
        params: { lines: 100, level: 'ERROR' },
      })
    })
  })
})
