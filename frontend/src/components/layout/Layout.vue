<template>
  <el-container class="layout-wrap">
    <!-- 左侧侧边栏 -->
    <el-aside width="230px" class="sidebar">
      <div class="logo-box">
        <h2>客服话术系统</h2>
      </div>
      <el-menu
        router
        background-color="#2f3947"
        text-color="#cbd5e0"
        active-text-color="#409eff"
        :default-active="route.path"
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
            <el-menu-item index="/workbench/admin/config">配置管理</el-menu-item>
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
    </el-aside>

    <!-- 右侧主容器 -->
    <el-container class="right-container">
      <!-- 顶部导航栏 -->
      <el-header class="header-bar">
        <div class="header-left">
          <!-- 可以在这里放面包屑或其他内容 -->
        </div>
        <div class="header-right">
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
        <div v-if="isImpersonating" class="impersonate-banner">
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
  </el-container>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Setting, DataLine, Ticket, Monitor, Money, ArrowLeft, Service, Document, UserFilled, WarningFilled } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()

// 获取当前用户信息
const currentRole = ref(sessionStorage.getItem('userRole') ?? '')
const userName = ref(sessionStorage.getItem('userName') ?? 'User')

// 监听路由变化，更新角色状态（防止手动修改sessionStorage后不刷新）
watch(() => sessionStorage.getItem('userRole'), (newVal) => {
  currentRole.value = newVal ?? ''
})

// 根据角色返回对应的中文名称
const roleText = computed(() => {
  switch (currentRole.value) {
    case 'admin': return '业务管理员'
    case 'superadmin': return '超级管理员'
    case 'ops': return '运维工程师'
    case 'service': return '客服'
    case 'dept': return '部门处理员'
    default: return '未知账号'
  }
})

// 模拟登录状态
const isImpersonating = computed(() => !!sessionStorage.getItem('impersonator_token'))

const exitImpersonate = () => {
  const origToken = sessionStorage.getItem('impersonator_token')
  const origRole = sessionStorage.getItem('impersonator_role')
  if (origToken) {
    sessionStorage.setItem('token', origToken)
    sessionStorage.setItem('userRole', origRole ?? 'superadmin')
    sessionStorage.removeItem('impersonator_token')
    sessionStorage.removeItem('impersonator_role')
    currentRole.value = origRole ?? 'superadmin'
    ElMessage.success('已退出模拟，返回超管身份')
    router.replace('/workbench/admin/account')
  }
}

// 判断是否显示返回按钮
const showBackBtn = computed(() => {
  const homePaths = ['/service', '/workbench/admin/auditList', '/workbench/admin/dashboard', '/workbench/admin/account', '/workbench/admin/status', '/dept/handle/aftersale', '/dept/handle/ops', '/dept/handle/finance']
  return !homePaths.includes(route.path)
})

// 返回上一页逻辑
const goBack = () => {
  if (window.history.length > 1) {
    router.back()
  } else {
    // 兜底逻辑
    if (currentRole.value === 'admin') router.push('/workbench/admin/auditList')
    else if (currentRole.value === 'ops') router.push('/workbench/admin/status')
    else if (currentRole.value === 'superadmin') router.push('/workbench/admin/account')
    else if (currentRole.value === 'service') router.push('/service')
    else router.push('/dept/handle/aftersale')
  }
}

// 退出登录
const handleCommand = (command: string) => {
  if (command === 'logout') {
    sessionStorage.clear()
    router.replace('/login')
    ElMessage.success('已退出登录')
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
  background-color: #2f3947;
  display: flex;
  flex-direction: column;
}
.logo-box {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  border-bottom: 1px solid #3b4a5a;
}
.side-menu {
  flex: 1;
  border-right: none;
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
</style>