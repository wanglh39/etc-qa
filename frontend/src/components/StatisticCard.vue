<template>
  <el-card class="stat-card">
    <div class="stat-top">
      <span class="stat-title">{{ title }}</span>
      <el-icon :size="24" :color="iconColor"><component :is="icon" /></el-icon>
    </div>
    <div class="stat-num">{{ value }}</div>
    <div class="stat-desc">{{ desc }}</div>
  </el-card>
</template>

<script setup lang="ts">
import type { Component } from 'vue'
defineProps<{
  title: string
  value: string | number
  desc: string
  icon: Component
  iconColor?: string
}>()
</script>

<style scoped>
.stat-card {
  height: 140px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}
.stat-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.stat-title {
  font-size: 14px;
  color: #666;
}
.stat-num {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}
.stat-desc {
  font-size: 12px;
  color: #999;
}
</style>
