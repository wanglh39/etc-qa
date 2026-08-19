import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const Layout = () => import('@/components/layout/Layout.vue')

// 区分角色默认首页
const DEFAULT_SERVICE_PATH = '/service'
const DEFAULT_ADMIN_PATH = '/workbench/admin/dashboard'

const routes: RouteRecordRaw[] = [
  // 1. 登录页
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/pages/login.vue'),
    meta: { title: '系统登录' }
  },

  // 2. 主布局嵌套路由
  {
    path: '/',
    component: Layout,
    redirect: DEFAULT_SERVICE_PATH,
    children: [
      // 管理员菜单页面
      {
        path: 'workbench/admin/auditList',
        name: 'AuditPendingNew',
        component: () => import('@/pages/audit/pending.vue'),
        meta: { title: '待审核列表', roleAuth: 'admin' }
      },
      {
        path: 'workbench/admin/auditHistory',
        name: 'AuditHistoryNew',
        component: () => import('@/pages/audit/history.vue'),
        meta: { title: '审核历史', roleAuth: 'admin' }
      },
      {
        path: 'workbench/admin/dashboard',
        name: 'DashboardNew',
        component: () => import('@/pages/dashboard/index.vue'),
        meta: { title: '数据看板', roleAuth: 'admin,ops' }
      },
      {
        path: 'workbench/admin/config',
        name: 'ConfigManage',
        component: () => import('@/pages/system/config.vue'),
        meta: { title: '配置管理', roleAuth: 'admin' }
      },
      {


        path: 'workbench/admin/knowledge',
        name: 'KnowledgeList',
        component: () => import('@/pages/knowledge/list.vue'),
        meta: { title: '知识库管理', roleAuth: 'admin' }
      },
      {
        path: 'workbench/admin/category',
        name: 'CategoryManage',
        component: () => import('@/pages/category/index.vue'),
        meta: { title: '分类管理', roleAuth: 'admin' }
      },
      {
        path: 'workbench/admin/account',
        name: 'AccountManage',
        component: () => import('@/pages/system/account.vue'),
        meta: { title: '账号管理', roleAuth: 'superadmin' }
      },
      {
        path: 'workbench/admin/role',
        name: 'RoleManage',
        component: () => import('@/pages/system/role.vue'),
        meta: { title: '角色管理', roleAuth: 'superadmin' }
      },
      {
        path: 'workbench/admin/operationLog',
        name: 'OperationLog',
        component: () => import('@/pages/system/operationLog.vue'),
        meta: { title: '操作日志', roleAuth: 'superadmin' }
      },
      {
        path: 'workbench/admin/impersonate',
        name: 'Impersonate',
        component: () => import('@/pages/system/impersonate.vue'),
        meta: { title: '模拟登录', roleAuth: 'superadmin' }
      },
      {
        path: 'workbench/admin/scheduler',
        name: 'Scheduler',
        component: () => import('@/pages/system/scheduler.vue'),
        meta: { title: '定时任务调度', roleAuth: 'ops' }
      },
      {
        path: 'workbench/admin/alert',
        name: 'Alert',
        component: () => import('@/pages/system/alert.vue'),
        meta: { title: '异常告警', roleAuth: 'ops' }
      },
      {
        path: 'workbench/admin/status',
        name: 'SystemStatus',
        component: () => import('@/pages/system/status.vue'),
        meta: { title: '系统状态总览', roleAuth: 'ops' }
      },
      {
        path: 'workbench/admin/monitor',
        name: 'SystemMonitor',
        component: () => import('@/pages/system/monitor.vue'),
        meta: { title: '性能监控看板', roleAuth: 'ops' }
      },
      {

        path: 'workbench/admin/pendingDetail',
        name: 'PendingDetail',
        component: () => import('@/pages/audit/pendingDetail.vue'),
        meta: { title: '工单审核详情', roleAuth: 'admin', hidden: true }
      },

      // CRM 模块
      {
        path: 'crm/create',
        name: 'CrmCreate',
        component: () => import('@/pages/service/crmCreate.vue'),
        meta: { title: '新建CRM工单', roleAuth: 'all' }
      },
      {
        path: 'crm/detail',
        name: 'CrmDetail',
        component: () => import('@/pages/service/crmDetail.vue'),
        meta: { title: '工单处理详情', roleAuth: 'all' }
      },
      {
        path: 'crm/list',
        name: 'CrmList',
        component: () => import('@/pages/service/crmList.vue'),
        meta: { title: 'CRM工单列表', roleAuth: 'all' }
      },

      // ================= 部门工单路由【修复版】 =================
      // 根路径重定向：根据 sessionStorage 中的 userDept 自动跳转
      {
        path: 'dept/handle',
        redirect: () => {
          const authStore = useAuthStore()
          return `/dept/handle/${authStore.dept || 'aftersale'}`
        }
      },
      // 统一动态路由：通过 :deptCode 捕获部门参数，所有部门共用页面
      {
        path: 'dept/handle/:deptCode',
        name: 'DeptWorkOrderHandle',
        component: () => import('@/pages/dept/WorkOrderHandle.vue'),
        meta: { title: '部门工单处理', roleAuth: 'dept' }
      },
      // 工单详情页（动态参数，隐藏菜单）
      {
        path: 'dept/handle/:deptCode/detail/:orderId',
        name: 'DeptWorkOrderDetail',
        component: () => import('@/pages/dept/WorkOrderHandleDetail.vue'),
        meta: { title: '工单详情', roleAuth: 'dept', hidden: true }
      },
      // ==========================================================

      // 旧兼容隐藏路由
      {
        path: 'audit/pending',
        name: 'AuditPending',
        component: () => import('@/pages/audit/pending.vue'),
        meta: { title: '旧待审核列表', hidden: true, roleAuth: 'admin' }
      },
      {
        path: 'audit/history',
        name: 'AuditHistory',
        component: () => import('@/pages/audit/history.vue'),
        meta: { title: '旧审核历史', hidden: true, roleAuth: 'admin' }
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/pages/dashboard/index.vue'),
        meta: { title: '旧数据看板', hidden: true, roleAuth: 'admin' }
      },
      {
        path: 'service',
        name: 'Service',
        component: () => import('@/pages/service/index.vue'),
        meta: { title: '客服工作台', roleAuth: 'service' }
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('@/pages/audit/index.vue'),
        meta: { title: '审核管理', roleAuth: 'admin', hidden: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 角色 → 默认首页
export function getDefaultPath(role: string): string {
  const authStore = useAuthStore()
  switch (role) {
    case 'superadmin':
      return '/workbench/admin/account'
    case 'ops':
      return '/workbench/admin/status'
    case 'admin':
      return DEFAULT_ADMIN_PATH
    case 'service':
      return DEFAULT_SERVICE_PATH
    case 'dept':
      return `/dept/handle/${authStore.dept || 'aftersale'}`
    default:
      return '/login'
  }
}

// 全局路由守卫：登录态 + 角色权限
let tokenVerified = false

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const token = authStore.token
  const role = authStore.role

  // 去登录页时重置验证标志
  if (to.path === '/login') {
    tokenVerified = false
    return next()
  }

  // 未登录 → 跳登录页
  if (!token) {
    ElMessage.warning('请先登录系统')
    return next('/login')
  }

  // token 过期检查：解码JWT看exp是否过期
  try {
    const payload = JSON.parse(atob(token.split('.')[1]))
    if (payload.exp && payload.exp * 1000 < Date.now()) {
      authStore.clearAuth()
      tokenVerified = false
      ElMessage.warning('登录已过期，请重新登录')
      return next('/login')
    }
  } catch {
    authStore.clearAuth()
    tokenVerified = false
    ElMessage.warning('登录信息异常，请重新登录')
    return next('/login')
  }

  // 首次导航时向后端验证token是否有效
  if (!tokenVerified) {
    try {
      const res = await fetch('/api/auth/verify', {
        headers: { Authorization: `Bearer ${token}` }
      })
      if (!res.ok) {
        authStore.clearAuth()
        tokenVerified = false
        ElMessage.warning('登录信息已失效，请重新登录')
        return next('/login')
      }
      tokenVerified = true
    } catch {
      authStore.clearAuth()
      tokenVerified = false
      ElMessage.warning('无法连接服务器，请重新登录')
      return next('/login')
    }
  }

  // 已登录但角色信息缺失（数据异常）→ 清理并重新登录
  if (token && !role) {
    authStore.clearAuth()
    tokenVerified = false
    ElMessage.warning('登录信息已失效，请重新登录')
    return next('/login')
  }

  // 角色权限校验：roleAuth 未设置或 'all' 表示所有已登录角色可访问
  // superadmin 可访问所有页面；支持逗号分隔多角色如 'admin,ops'
  const roleAuth = to.meta.roleAuth as string | undefined
  if (roleAuth && roleAuth !== 'all') {
    if (role !== 'superadmin') {
      const allowedRoles = roleAuth.split(',').map(r => r.trim())
      if (!allowedRoles.includes(role!)) {
        ElMessage.warning('无权访问该页面')
        return next(getDefaultPath(role!))
      }
    }
  }

  next()
})

export default router