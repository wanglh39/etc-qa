<template>
  <div class="top-navbar">
    <div class="navbar-left">
      <el-menu mode="horizontal" :default-active="activeMenu" class="nav-menu">
        <el-menu-item index="/workbench"> 智能问答工作台 </el-menu-item>
        <el-menu-item index="/knowledge"> 知识列表 </el-menu-item>
        <el-menu-item index="/category"> 分类管理 </el-menu-item>
        <el-menu-item index="/audit/pending"> 审核中心 </el-menu-item>
      </el-menu>
    </div>
    <div class="navbar-right">
      <el-badge :value="noticeNum" :hidden="noticeNum === 0">
        <el-button link>
          <Bell />
          消息通知
        </el-button>
      </el-badge>
      <el-dropdown>
        <span class="user-info">
          <el-avatar :size="32" />
          <span>管理员</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item>个人中心</el-dropdown-item>
            <el-dropdown-item @click="logout"> 退出登录 </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useSessionStore } from '@/store/session'
import { Bell } from '@element-plus/icons-vue'
const router = useRouter()
const sessionStore = useSessionStore()
const noticeNum = sessionStore.pendingTicketNum
const activeMenu = router.currentRoute.value.path
const logout = () => {
  router.push('/login')
}
</script>

<style scoped>
.top-navbar {
  height: 56px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 24px;
}
.navbar-left {
  display: flex;
  align-items: center;
}
.nav-menu {
  border: none;
  background: transparent;
}
.navbar-right {
  display: flex;
  align-items: center;
  gap: 24px;
}
.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  color: #475569;
}
</style>
