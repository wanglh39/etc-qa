<template>
  <div class="sidebar-menu">
    <div class="sidebar-title">后台管理系统菜单</div>
    <el-menu
      mode="vertical"
      router
      :default-active="$route.path"
      background-color="#ffffff"
      text-color="#333"
      active-text-color="#0052FF"
      class="menu-wrap"
    >
      <!-- 循环渲染菜单 -->
      <template v-for="route in menuList" :key="route.path || route.name">
        
        <!-- 情况A：有子菜单的父级菜单 (例如：部门工单处理) -->
        <el-sub-menu
          v-if="route.children && route.children.length > 0"
          :index="route.path"
        >
          <template #title>
            <span>{{ route.meta?.title || '未命名菜单' }}</span>
          </template>
          
          <el-menu-item
            v-for="child in route.children"
            :key="child.path"
            :index="child.path"
          >
            {{ child.meta?.title || '未命名子菜单' }}
          </el-menu-item>
        </el-sub-menu>

        <!-- 情况B：没有子菜单的直接跳转项 -->
        <el-menu-item 
          v-else 
          :index="route.path.startsWith('/') ? route.path : `/${route.path}`"
        >
          {{ route.meta?.title || '未命名菜单' }}
        </el-menu-item>
      </template>
    </el-menu>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// 1. 定义菜单项的接口类型，解决 TS 报错
interface MenuItem extends Omit<RouteRecordRaw, 'children'> {
  children?: MenuItem[]
  meta?: {
    title?: string
    hidden?: boolean
    roleAuth?: string
    [key: string]: any
  }
}

const router = useRouter()
const authStore = useAuthStore()

const userRole = computed(() => authStore.role)
const userDept = computed(() => authStore.dept)

// 定义部门映射配置
const DEPT_CONFIG = [
  { code: 'aftersale', name: '售后工单处理' },
  { code: 'ops', name: '技术运维工单处理' },
  { code: 'finance', name: '财务工单处理' },
  { code: 'market', name: '市场工单处理' },
  { code: 'human', name: '人事工单处理' }
]

// 计算最终要显示的菜单列表
const menuList = computed<MenuItem[]>(() => {
  const layoutRoute = router.options.routes.find(item => item.path === '/')
  if (!layoutRoute?.children) return []

  // 1. 基础过滤：隐藏页面(hidden=true)不显示
  let baseRoutes = layoutRoute.children.filter((item: any) => !item.meta?.hidden) as MenuItem[]

  // 2. 根据角色进行特殊处理
  if (userRole.value === 'dept') {
    // --- 部门处理员逻辑 ---
    
    // A. 过滤掉管理员专用的路由
    baseRoutes = baseRoutes.filter((r) => r.meta?.roleAuth !== 'admin')

    // B. 移除原始的 "dept/handle/:deptCode" 这种带参数的通用路由
    baseRoutes = baseRoutes.filter((r) => !r.path.includes(':deptCode'))

    // C. 构造具体的部门菜单
    const deptParentPath = 'dept/handle'
    
    // 构造部门子菜单列表 (明确指定类型为 MenuItem)
    const deptChildren: MenuItem[] = DEPT_CONFIG.map(dept => ({
      path: `/${deptParentPath}/${dept.code}`, 
      meta: { title: dept.name },
      name: `DeptHandle_${dept.code}`
    }))

    // 找到原来的父级路由对象以便保留其 title
    const originalParent = baseRoutes.find((r) => r.path === deptParentPath)
    
    // 构造生成的父级菜单对象
    const generatedDeptMenu: MenuItem = {
      path: `/${deptParentPath}`,
      meta: { title: originalParent?.meta?.title || '部门工单处理' },
      children: deptChildren,
      name: 'DeptHandleRoot' // 补上 name 防止报错
    }

    // 将生成的部门菜单加入列表，并移除原本空的父级路由
    const otherRoutes = baseRoutes.filter((r) => r.path !== deptParentPath)
    return [...otherRoutes, generatedDeptMenu]

  } else if (userRole.value === 'service') {
    // --- 客服逻辑 ---
    return baseRoutes.filter((r) => {
      const auth = r.meta?.roleAuth || 'all'
      return auth === 'all' || auth === 'service'
    })
  } else {
    // --- 管理员/默认逻辑 ---
    return baseRoutes
  }
})
</script>

<style scoped>
.sidebar-menu {
  width: 220px;
  height: 100vh;
  background: #fff;
  border-right: 1px solid #ebeef5;
  position: relative;
  z-index: 9999;
  box-sizing: border-box;
}

.sidebar-title {
  height: 50px;
  line-height: 50px;
  text-align: center;
  font-size: 16px;
  font-weight: bold;
  color: #333;
  border-bottom: 1px solid #ebeef5;
}

.menu-wrap {
  border-right: none;
}
</style>