<template>
  <el-card>
    <template #header>审核历史记录</template>
    <el-table :data="historyList" border v-loading="loading">
      <el-table-column prop="id" label="审核编号" width="100"/>
      <el-table-column prop="question" label="审核问题" min-width="200"/>

      <!-- 标准化答案字段 -->
      <el-table-column prop="answer" label="标准化答案" min-width="200">
        <template #default="{row}">
          <span style="color: #909399;">{{ row.answer || '暂无' }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="result" label="审核结果" width="100">
        <template #default="{row}">
          <el-tag :type="row.result === 'pass' ? 'success' : 'danger'">
            {{ row.result === 'pass' ? '入库' : '驳回' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="operator" label="操作管理员" width="120"/>
      <el-table-column prop="created_at" label="审核时间" width="180"/>
    </el-table>
    <el-pagination
      v-model:current-page="page"
      v-model:page-size="pageSize"
      :total="total"
      layout="total, prev, pager, next"
      style="margin-top: 16px; justify-content: flex-end; display: flex"
      @current-change="loadData"
    />
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getAuditHistory, type AuditLogItem } from '@/api/audit'

const historyList = ref<AuditLogItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const loadData = async () => {
  loading.value = true
  try {
    const res = await getAuditHistory({ page: page.value, page_size: pageSize.value })
    historyList.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载审核历史失败')
  } finally {
    loading.value = false
  }
}

onMounted(loadData)
</script>
