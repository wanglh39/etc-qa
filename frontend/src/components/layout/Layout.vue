<template>
  <el-container class="layout-wrap">
    <!-- 左侧侧边栏 -->
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="logo-box">
        <el-icon :size="24" color="#409eff"><Headset /></el-icon>
        <span v-if="!collapsed" class="logo-text">智能客服系统</span>
      </div>
      <el-menu
        router
        background-color="#2f3947"
        text-color="#cbd5e0"
        active-text-color="#409eff"
        :default-active="route.path"
        :collapse="collapsed"
        :collapse-transition="true"
        class="side-menu"
      >
        <!-- 超级管理员菜单 -->
        <template v-if="currentRole === 'superadmin'">
          <el-sub-menu index="system">
            <template #title>
              <el-icon><UserFilled /></el-icon>
              <span>系统管理</span>
            </template>
            <el-menu-item index="/workbench/admin/account">账号管理</el-menu-item>
            <el-menu-item index="/workbench/admin/role">角色管理</el-menu-item>
            <el-menu-item index="/workbench/admin/operationLog">操作日志</el-menu-item>
            <el-menu-item index="/workbench/admin/impersonate">模拟登录</el-menu-item>
          </el-sub-menu>
        </template>

        <!-- 运维工程师菜单 -->
        <template v-else-if="currentRole === 'ops'">
          <el-menu-item index="/workbench/admin/dashboard">
            <el-icon><DataLine /></el-icon>
            <span>数据看板</span>
          </el-menu-item>
          <el-sub-menu index="ops-mgmt">
            <template #title>
              <el-icon><Monitor /></el-icon>
              <span>运维管理</span>
            </template>
            <el-menu-item index="/workbench/admin/status">系统状态总览</el-menu-item>
            <el-menu-item index="/workbench/admin/monitor">性能监控看板</el-menu-item>
            <el-menu-item index="/workbench/admin/scheduler">定时任务调度</el-menu-item>
            <el-menu-item index="/workbench/admin/alert">异常告警</el-menu-item>
          </el-sub-menu>
        </template>

        <!-- 业务管理员菜单 -->
        <template v-else-if="currentRole === 'admin'">
          <el-menu-item index="/workbench/admin/dashboard">
            <el-icon><DataLine /></el-icon>
            <span>数据看板</span>
          </el-menu-item>
          <el-sub-menu index="business">
            <template #title>
              <el-icon><Setting /></el-icon>
              <span>业务管理</span>
            </template>
            <el-menu-item index="/workbench/admin/auditList">待审核列表</el-menu-item>
            <el-menu-item index="/workbench/admin/auditHistory">审核历史</el-menu-item>
          </el-sub-menu>
          <el-sub-menu index="content">
            <template #title>
              <el-icon><Document /></el-icon>
              <span>内容管理</span>
            </template>
            <el-menu-item index="/workbench/admin/knowledge">知识库管理</el-menu-item>
            <el-menu-item index="/workbench/admin/category">分类管理</el-menu-item>
            <el-menu-item index="/workbench/admin/prompt">提示词管理</el-menu-item>
            <el-menu-item index="/workbench/admin/config">配置管理</el-menu-item>
            <el-menu-item index="/workbench/admin/shadowTest">A/B影子测试</el-menu-item>
          </el-sub-menu>
        </template>

        <!-- 客服菜单 -->
        <template v-else-if="currentRole === 'service'">
          <el-menu-item index="/service">
            <el-icon><Service /></el-icon>
            <span>客服工作台</span>
          </el-menu-item>
        </template>

        <!-- 部门处理员菜单 -->
        <template v-else-if="currentRole === 'dept'">
          <el-menu-item index="/dept/handle/aftersale">
            <el-icon><Ticket /></el-icon>
            <span>售后工单处理</span>
          </el-menu-item>
          <el-menu-item index="/dept/handle/ops">
            <el-icon><Monitor /></el-icon>
            <span>技术运维工单处理</span>
          </el-menu-item>
          <el-menu-item index="/dept/handle/finance">
            <el-icon><Money /></el-icon>
            <span>财务工单处理</span>
          </el-menu-item>
        </template>
      </el-menu>

      <!-- 侧边栏底部用户区 -->
      <div class="sidebar-footer" v-if="!collapsed">
        <el-avatar :size="36" class="user-avatar">{{ roleText.charAt(0) }}</el-avatar>
        <div class="user-detail">
          <span class="user-name">{{ authStore.username || roleText }}</span>
          <span class="user-role">{{ roleText }}</span>
        </div>
      </div>
    </el-aside>

    <!-- 右侧主容器 -->
    <el-container class="right-container">
      <!-- 顶部导航栏 -->
      <el-header class="header-bar">
        <div class="header-left">
          <el-icon class="collapse-btn" @click="collapsed = !collapsed">
            <Fold v-if="!collapsed" />
            <Expand v-else />
          </el-icon>
          <BreadCrumb />
        </div>
        <div class="header-right">
          <el-badge :value="unreadAlerts" :hidden="unreadAlerts === 0" :max="99">
            <el-icon class="header-icon" @click="goToAlerts"><Bell /></el-icon>
          </el-badge>
          <el-tooltip content="快捷搜索 (Ctrl+K)" placement="bottom">
            <el-icon class="header-icon" @click="commandPaletteVisible = true"><Search /></el-icon>
          </el-tooltip>
          <el-dropdown @command="handleCommand">
            <span class="user-info">
              <el-avatar :size="32">{{ roleText.charAt(0) }}</el-avatar>
              <span class="username">{{ roleText }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <!-- 主体内容区 -->
      <el-main class="main-content">
        <!-- 模拟登录提示栏 -->
        <div v-if="authStore.isImpersonating" class="impersonate-banner">
          <el-icon><WarningFilled /></el-icon>
          <span>您正在以【{{ roleText }}】身份查看，操作会记录到日志</span>
          <el-button type="danger" size="small" @click="exitImpersonate">退出模拟</el-button>
        </div>

        <!-- 页面顶部操作栏：放置返回按钮 -->
        <div class="page-header" v-if="showBackBtn">
          <el-button link type="primary" size="large" @click="goBack">
            <el-icon style="margin-right: 4px"><ArrowLeft /></el-icon>
            返回
          </el-button>
        </div>

        <!-- 原有业务内容区 -->
        <div class="content-box">
          <router-view />
        </div>
      </el-main>
    </el-container>

    <!-- 命令面板 -->
    <el-dialog
      v-model="commandPaletteVisible"
      title="快捷导航"
      width="480px"
      :show-close="false"
      append-to-body
      @opened="focusPaletteInput"
    >
      <el-input
        ref="paletteInputRef"
        v-model="paletteQuery"
        placeholder="输入页面名称搜索..."
        :prefix-icon="Search"
        clearable
        @keydown.down.prevent="paletteDown"
        @keydown.up.prevent="paletteUp"
        @keydown.enter.prevent="paletteSelect"
      />
      <div class="palette-list">
        <div
          v-for="(item, idx) in paletteResults"
          :key="item.path"
          class="palette-item"
          :class="{ active: idx === paletteIndex }"
          @click="paletteNavigate(item.path)"
          @mouseenter="paletteIndex = idx"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
          <span class="palette-path">{{ item.path }}</span>
        </div>
        <el-empty v-if="paletteResults.length === 0" description="无匹配页面" :image-size="60" />
      </div>
    </el-dialog>
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Setting, DataLine, Ticket, Monitor, Money, ArrowLeft, Service, Document, UserFilled, WarningFilled, Fold, Expand, Headset, Bell, Search } from '@element-plus/icons-vue'
import { ElMessage, type InputInstance } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getAlertList } from '@/api/system'
import BreadCrumb from '@/components/BreadCrumb.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)
const sidebarWidth = computed(() => collapsed.value ? '64px' : '230px')
const currentRole = computed(() => authStore.role)
const roleText = computed(() => authStore.roleText)

const exitImpersonate = () => {
  authStore.exitImpersonation()
  ElMessage.success('已退出模拟，返回超管身份')
  router.replace('/workbench/admin/account')
}

const showBackBtn = computed(() => {
  const homePaths = ['/service', '/workbench/admin/auditList', '/workbench/admin/dashboard', '/workbench/admin/account', '/workbench/admin/status', '/dept/handle/aftersale', '/dept/handle/ops', '/dept/handle/finance']
  return !homePaths.includes(route.path)
})

const goBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    if (currentRole.value === 'admin') router.push('/workbench/admin/dashboard')
    else if (currentRole.value === 'ops') router.push('/workbench/admin/status')
    else if (currentRole.value === 'superadmin') router.push('/workbench/admin/account')
    else if (currentRole.value === 'service') router.push('/service')
    else router.push('/dept/handle/aftersale')
  }
}

const handleCommand = (command: string) => {
  if (command === 'logout') {
    authStore.clearAuth()
    router.replace('/login')
    ElMessage.success('已退出登录')
  }
}

// ===== 通知铃铛 =====
const unreadAlerts = ref(0)
const goToAlerts = () => {
  router.push('/workbench/admin/alert')
}
const loadUnreadAlerts = async () => {
  if (!['ops', 'admin', 'superadmin'].includes(currentRole.value)) return
  try {
    const res = await getAlertList({ status: 'active', page: 1, page_size: 1 })
    unreadAlerts.value = (res as any).total || 0
  } catch {
    unreadAlerts.value = 0
  }
}

// ===== 命令面板 =====
const commandPaletteVisible = ref(false)
const paletteQuery = ref('')
const paletteIndex = ref(0)
const paletteInputRef = ref<InputInstance>()

interface PaletteItem {
  label: string
  path: string
  icon: any
}

const allPages: PaletteItem[] = [
  { label: '数据看板', path: '/workbench/admin/dashboard', icon: DataLine },
  { label: '知识库管理', path: '/workbench/admin/knowledge', icon: Document },
  { label: '分类管理', path: '/workbench/admin/category', icon: Setting },
  { label: '待审核列表', path: '/workbench/admin/auditList', icon: Document },
  { label: '审核历史', path: '/workbench/admin/auditHistory', icon: Document },
  { label: '配置管理', path: '/workbench/admin/config', icon: Setting },
  { label: '提示词管理', path: '/workbench/admin/prompt', icon: Document },
  { label: 'A/B影子测试', path: '/workbench/admin/shadowTest', icon: Setting },
  { label: '账号管理', path: '/workbench/admin/account', icon: UserFilled },
  { label: '角色管理', path: '/workbench/admin/role', icon: UserFilled },
  { label: '操作日志', path: '/workbench/admin/operationLog', icon: Document },
  { label: '模拟登录', path: '/workbench/admin/impersonate', icon: UserFilled },
  { label: '系统状态', path: '/workbench/admin/status', icon: Monitor },
  { label: '性能监控', path: '/workbench/admin/monitor', icon: Monitor },
  { label: '定时任务', path: '/workbench/admin/scheduler', icon: Setting },
  { label: '异常告警', path: '/workbench/admin/alert', icon: Bell },
  { label: '客服工作台', path: '/service', icon: Service },
  { label: '售后工单', path: '/dept/handle/aftersale', icon: Ticket },
  { label: '运维工单', path: '/dept/handle/ops', icon: Monitor },
  { label: '财务工单', path: '/dept/handle/finance', icon: Money },
]

const paletteResults = computed(() => {
  const q = paletteQuery.value.toLowerCase()
  if (!q) return allPages.slice(0, 8)
  return allPages.filter((p) => p.label.toLowerCase().includes(q) || p.path.toLowerCase().includes(q))
})

const focusPaletteInput = () => {
  paletteInputRef.value?.focus()
}
const paletteDown = () => {
  if (paletteIndex.value < paletteResults.value.length - 1) paletteIndex.value++
}
const paletteUp = () => {
  if (paletteIndex.value > 0) paletteIndex.value--
}
const paletteSelect = () => {
  const item = paletteResults.value[paletteIndex.value]
  if (item) paletteNavigate(item.path)
}
const paletteNavigate = (path: string) => {
  commandPaletteVisible.value = false
  paletteQuery.value = ''
  paletteIndex.value = 0
  router.push(path)
}

const onKeydown = (e: KeyboardEvent) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    commandPaletteVisible.value = true
  }
}

onMounted(() => {
  loadUnreadAlerts()
  window.addEventListener('keydown', onKeydown)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKeydown)
})
</script>

<style scoped>
.layout-wrap {
  height: 100vh;
  display: flex;
  width: 100%;
}
.sidebar {
  height: 100vh;
  background-color: #2f3947;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
}
.logo-box {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: #fff;
  border-bottom: 1px solid #3b4a5a;
  flex-shrink: 0;
}
.logo-text {
  font-size: 16px;
  font-weight: 600;
  white-space: nowrap;
}
.side-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
}
.sidebar-footer {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  border-top: 1px solid #3b4a5a;
  flex-shrink: 0;
}
.user-avatar {
  background: #409eff;
  font-weight: 600;
  flex-shrink: 0;
}
.user-detail {
  display: flex;
  flex-direction: column;
  gap: 2px;
  overflow: hidden;
}
.user-name {
  color: #fff;
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-role {
  color: #909399;
  font-size: 12px;
}
.right-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.header-bar {
  height: 60px;
  background-color: #fff;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #606266;
  transition: color 0.2s;
}
.collapse-btn:hover {
  color: #409eff;
}
.user-info {
  display: flex;
  align-items: center;
  cursor: pointer;
  gap: 8px;
}
.main-content {
  flex: 1;
  padding: 0;
  background-color: #f5f7fa;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.page-header {
  height: 50px;
  padding: 0 20px;
  background-color: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.content-box {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
}
.impersonate-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background-color: #fdf6ec;
  border-bottom: 1px solid #f5dab1;
  color: #e6a23c;
  font-size: 13px;
  flex-shrink: 0;
}
.impersonate-banner .el-button {
  margin-left: auto;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 20px;
}
.header-icon {
  font-size: 18px;
  cursor: pointer;
  color: #606266;
  transition: color 0.2s;
}
.header-icon:hover {
  color: #409eff;
}
.palette-list {
  margin-top: 12px;
  max-height: 320px;
  overflow-y: auto;
}
.palette-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.15s;
}
.palette-item.active {
  background: #ecf5ff;
}
.palette-item:hover {
  background: #f5f7fa;
}
.palette-path {
  margin-left: auto;
  font-size: 12px;
  color: #c0c4cc;
}
</style>
