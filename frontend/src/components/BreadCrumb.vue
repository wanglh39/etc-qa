<template>
  <el-breadcrumb separator="/">
    <el-breadcrumb-item to="/">首页</el-breadcrumb-item>
    <el-breadcrumb-item v-for="item in breadList" :key="item.path" :to="item.path">
      {{ item.meta?.title }}
    </el-breadcrumb-item>
  </el-breadcrumb>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
const route = useRoute()
// 自动根据路由匹配面包屑
const breadList = computed(() => {
  return route.matched.filter((item) => item.meta?.title && item.path !== '/')
})
</script>
