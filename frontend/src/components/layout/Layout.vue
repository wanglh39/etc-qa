<template>
  <el-container class="layout-wrap">
    <!-- 左侧侧边栏 -->
    <el-aside :width="sidebarWidth" class="sidebar">
      <div class="logo-box">
        <el-icon :size="20" color="#1677FF"><Headset /></el-icon>
        <span v-if="!collapsed" class="logo-text">智能客服系统</span>
      </div>
      <el-menu
        router
        background-color="transparent"
        text-color="#475569"
        active-text-color="#0F172A"
        :default-active="route.path"
        :collapse="collapsed"
        :collapse-transition="true"
        class="side-menu"
      >
        <template v-for="group in menuGroups" :key="group.label || group.items[0].path">
          <el-sub-menu v-if="group.label" :index="group.label">
            <template #title>
              <el-icon><component :is="group.icon" /></el-icon>
              <span>{{ group.label }}</span>
            </template>
            <el-menu-item v-for="item in group.items" :key="item.path" :index="item.path">
              {{ item.label }}
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="group.items[0].path">
            <el-icon><component :is="group.items[0].icon" /></el-icon>
            <span>{{ group.items[0].label }}</span>
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
          <el-button type="primary" size="small" @click="exitImpersonate">退出模拟</el-button>
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

  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, WarningFilled, Fold, Expand, Headset, Bell } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { getAlertList, getMyPermissions } from '@/api/system'
import { buildMenu, type MenuGroup } from '@/config/pages'
import { getDefaultPath } from '@/router'
import BreadCrumb from '@/components/BreadCrumb.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const menuGroups = ref<MenuGroup[]>([])

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
    router.push(getDefaultPath(currentRole.value))
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
  const hasAlertPage = menuGroups.value.some(g => g.items.some(i => i.path === '/workbench/admin/alert'))
  if (!hasAlertPage) return
  try {
    const res = await getAlertList({ status: 'active', page: 1, page_size: 1 })
    unreadAlerts.value = (res as any).total || 0
  } catch {
    unreadAlerts.value = 0
  }
}

onMounted(async () => {
  await loadMenu()
  loadUnreadAlerts()
})

watch(currentRole, async () => {
  await loadMenu()
  loadUnreadAlerts()
})

const loadMenu = async () => {
  try {
    const perms = await getMyPermissions()
    authStore.setPermissions(perms)
    menuGroups.value = buildMenu(perms)
  } catch {
    menuGroups.value = []
  }
}

</script>

<style scoped>
.layout-wrap {
  height: 100vh;
  display: flex;
  width: 100%;
}
.sidebar {
  height: 100vh;
  background-color: #FFFFFF;
  display: flex;
  flex-direction: column;
  transition: width 0.3s ease;
  overflow: hidden;
  border-right: 1px solid #E2E8F0;
}
.logo-box {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #0F172A;
  flex-shrink: 0;
}
.logo-text {
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  letter-spacing: -0.01em;
}
.side-menu {
  flex: 1;
  border-right: none;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 4px 8px;
}
:deep(.side-menu .el-menu-item) {
  border-radius: 6px;
  margin: 2px 0;
  height: 36px;
  line-height: 36px;
}
:deep(.side-menu .el-menu-item.is-active) {
  background-color: #F1F5F9 !important;
  color: #0F172A !important;
  font-weight: 600;
}
:deep(.side-menu .el-menu-item:hover) {
  background-color: #F1F5F9 !important;
}
:deep(.side-menu .el-sub-menu__title) {
  border-radius: 6px;
  margin: 2px 0;
  height: 36px;
  line-height: 36px;
}
:deep(.side-menu .el-sub-menu__title:hover) {
  background-color: #F1F5F9 !important;
}
:deep(.side-menu .el-sub-menu .el-menu-item.is-active) {
  background-color: #F1F5F9 !important;
  color: #0F172A !important;
  font-weight: 600;
}
.sidebar-footer {
  height: 56px;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-top: 1px solid #E2E8F0;
  flex-shrink: 0;
}
.user-avatar {
  background: #F1F5F9;
  color: #475569;
  font-weight: 600;
  flex-shrink: 0;
}
.user-detail {
  display: flex;
  flex-direction: column;
  gap: 1px;
  overflow: hidden;
}
.user-name {
  color: #0F172A;
  font-size: 13px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.user-role {
  color: #94A3B8;
  font-size: 12px;
}
.right-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.header-bar {
  height: 52px;
  background-color: #FFFFFF;
  border-bottom: 1px solid #E2E8F0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}
.collapse-btn {
  font-size: 20px;
  cursor: pointer;
  color: #475569;
  transition: color 0.2s;
}
.collapse-btn:hover {
  color: #1677FF;
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
  background-color: var(--color-bg-canvas);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.page-header {
  height: 50px;
  padding: 0 20px;
  background-color: #fff;
  border-bottom: 1px solid #E2E8F0;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
.content-box {
  flex: 1;
  padding: 16px;
  overflow-y: auto;
}
.impersonate-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  background-color: #E6F4FF;
  border-bottom: 1px solid #91CAFF;
  color: #475569;
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
  color: #475569;
  transition: color 0.2s;
}
.header-icon:hover {
  color: #1677FF;
}

</style>
