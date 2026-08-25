<template>
  <div class="page-container">
    <el-card class="page-card">
      <template #header>
        <div class="page-header">
          <span class="page-title">{{ pageTitle }}</span>
          <!-- 右上角功能按钮插槽 -->
          <div class="page-actions">
            <slot name="actions" />
          </div>
        </div>
      </template>
      <!-- 页面主体内容插槽 -->
      <div class="page-content">
        <slot />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
defineProps({
  pageTitle: {
    type: String,
    required: true,
  },
})
</script>

<style scoped>
.page-card {
  width: 100%;
}
.page-content {
  margin-top: 16px;
}
</style>
