<template>
  <el-dialog v-model="visible" :title="title" width="500px" @close="$emit('close')">
    <slot>弹窗内容</slot>
    <template #footer>
      <el-button @click="$emit('close')">取消</el-button>
      <el-button type="primary" @click="$emit('confirm')">确认</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
// 把props里的visible替换成defineModel，实现双向绑定
const visible = defineModel<boolean>('visible', { required: true })
defineProps<{
  title: string
}>()
defineEmits(['confirm', 'close'])
</script>
