<template>
  <div class="not-found">
    <div class="content">
      <div class="code">404</div>
      <div class="desc">页面不存在或已被移除</div>
      <el-button type="primary" @click="goHome">返回首页</el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { getDefaultPath } from '@/router'

const router = useRouter()
const authStore = useAuthStore()

const goHome = () => {
  router.push(getDefaultPath(authStore.role))
}
</script>

<style scoped>
.not-found {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F8FAFC;
}
.content {
  text-align: center;
}
.code {
  font-size: 72px;
  font-weight: 700;
  color: #1677FF;
  letter-spacing: -0.04em;
  line-height: 1;
}
.desc {
  font-size: 15px;
  color: #64748B;
  margin: 12px 0 28px;
}
</style>