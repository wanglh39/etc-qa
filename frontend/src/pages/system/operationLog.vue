<template>
  <div class="oplog-wrap">
    <el-card class="full-card">
      <div class="card-body-inner">
        <h3>操作日志</h3>

        <div class="filter-bar">
          <el-input
            v-model="filterOperator"
            placeholder="操作人筛选"
            clearable
            style="width: 180px"
            @keyup.enter="handleSearch"
          />
          <el-select
            v-model="filterAction"
            placeholder="动作筛选"
            clearable
            style="width: 160px; margin-left: 12px"
            @change="handleSearch"
          >
            <el-option label="创建" value="create" />
            <el-option label="修改" value="update" />
            <el-option label="删除" value="delete" />
            <el-option label="重置密码" value="reset_password" />
          </el-select>
          <el-button type="primary" style="margin-left: 12px" @click="handleSearch">搜索</el-button>
          <el-button style="margin-left: 8px" @click="handleReset">重置</el-button>
        </div>

        <el-table border :max-height="'calc(100vh - 300px)'" :data="tableData">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column prop="operator" label="操作人" width="120" />
          <el-table-column label="动作" width="100">
            <template #default="{ row }">
              <el-tag :type="actionTagType(row.action)">{{ actionLabel(row.action) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="target_type" label="对象类型" width="100" />
          <el-table-column prop="target_id" label="对象ID" width="80" />
          <el-table-column prop="detail" label="详情" min-width="250" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" width="170" />
        </el-table>

        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          :total="total"
          layout="total, sizes, prev, pager, next, jumper"
          style="margin-top: 18px; justify-content: flex-end; display: flex"
          @current-change="loadData"
          @size-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getOperationList, type OperationLogItem } from '@/api/system'

const filterOperator = ref('')
const filterAction = ref('')
const page = ref(1)
const pageSize = ref(20)
const tableData = ref<OperationLogItem[]>([])
const total = ref(0)

const actionLabel = (a: string) => {
  const map: Record<string, string> = { create: '创建', update: '修改', delete: '删除', reset_password: '重置密码' }
  return map[a] || a
}
const actionTagType = (a: string) => {
  const map: Record<string, string> = { create: 'success', update: 'warning', delete: 'danger', reset_password: 'info' }
  return map[a] || 'info'
}

const loadData = async () => {
  try {
    const res = await getOperationList({
      page: page.value,
      page_size: pageSize.value,
      operator: filterOperator.value || undefined,
      action: filterAction.value || undefined
    })
    tableData.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载操作日志失败')
  }
}

const handleSearch = () => {
  page.value = 1
  loadData()
}
const handleReset = () => {
  filterOperator.value = ''
  filterAction.value = ''
  page.value = 1
  loadData()
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.oplog-wrap {
  width: 100%;
  height: 100vh;
  padding: 20px;
  box-sizing: border-box;
  overflow: hidden;
}
.full-card {
  height: 100%;
}
:deep(.el-card__body) {
  height: 100%;
  padding: 20px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.card-body-inner {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.filter-bar {
  margin: 12px 0;
  display: flex;
  align-items: center;
}
.el-table {
  width: 100%;
}
</style>