<template>
  <div class="batch-table">
    <!-- 批量操作栏 -->
    <div class="batch-bar" v-if="showBatch">
      <el-space>
        <el-button type="primary" @click="batchHandle">批量{{ batchText }}</el-button>
        <el-button @click="clearSelection">清空选中</el-button>
        <span v-if="selectedList.length > 0">已选中{{ selectedList.length }}条数据</span>
      </el-space>
    </div>
    <!-- 表格主体 -->
    <el-table
      ref="tableRef"
      border
      stripe
      row-key="id"
      :data="tableData"
      @selection-change="handleSelectionChange"
      v-bind="$attrs"
    >
      <el-table-column type="selection" width="55" v-if="showBatch" />
      <slot />
    </el-table>
    <!-- 分页 -->
    <el-pagination
      class="mt-4"
      background
      layout="total, sizes, prev, pager, next, jumper"
      :total="total"
      :page-size="pageSize"
      :current-page="pageNum"
      @size-change="(val:number) => {
        emit('update:pageSize', val)
        emit('page-change')
      }"
      @current-change="(val:number) => {
        emit('update:pageNum', val)
        emit('page-change')
      }"
    />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'

const tableRef = ref()
const selectedList = ref<any[]>([])

const props = defineProps<{
  tableData: any[]
  total: number
  pageNum: number
  pageSize: number
  showBatch?: boolean
  batchText?: string
}>()
const emit = defineEmits(['batch', 'page-change', 'update:pageNum', 'update:pageSize'])

const handleSelectionChange = (val: any[]) => {
  selectedList.value = val
}
const batchHandle = () => {
  if (selectedList.value.length === 0) return ElMessage.warning('请先勾选需要操作的数据')
  emit('batch', selectedList.value)
}
const clearSelection = () => {
  tableRef.value.clearSelection()
  selectedList.value = []
}
</script>

<style scoped>
.batch-bar {
  margin-bottom: 12px;
}
.mt-4 {
  margin-top: 16px;
}
</style>