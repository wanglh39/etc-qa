import { createRouter, createWebHistory, RouteRecordRaw } from 'vue-router'
import { ElMessage } from 'element-plus'

const Layout = () => import('@/components/layout/Layout.vue')

// 区分角色默认首页
const DEFAULT_SERVICE_PATH = '/workbench/smart'
const DEFAULT_ADMIN_PATH = '/workbench/admin/auditList'

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
      // 2.1 智能问答工作台（客服默认首页）
      {
        path: 'workbench/smart',
        name: 'SmartWorkbench',
        component: () => import('@/pages/workbench/SmartWorkbench.vue'),
        meta: { title: '智能问答工作台', roleAuth: 'all' }
      },

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
        meta: { title: '数据看板', roleAuth: 'admin' }
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
      // 根路径重定向：根据 localStorage 中的 userDept 自动跳转
      {
        path: 'dept/handle',
        redirect: () => {
          const userDept = localStorage.getItem('userDept') || 'aftersale'
          return `/dept/handle/${userDept}`
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
        meta: { title: '服务管理', roleAuth: 'all', hidden: true }
      },
      {
        path: 'audit',
        name: 'Audit',
        component: () => import('@/pages/audit/index.vue'),
        meta: { title: '审核管理', roleAuth: 'admin' }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 全局路由守卫（可选，保留原有权限逻辑）
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (to.path !== '/login' && !token) {
    ElMessage.warning('请先登录系统')
    return next('/login')
  }
  next()
})

export default router