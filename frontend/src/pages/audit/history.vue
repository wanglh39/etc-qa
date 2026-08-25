<template>
  <div class="audit-history-wrap">
    <!-- KPI 概览卡片 -->
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-icon">
          <el-icon :size="24">
            <DataLine />
          </el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">
            {{ total }}
          </div>
          <div class="kpi-label">总审核数</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">
          <el-icon :size="24">
            <CircleCheck />
          </el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">
            {{ passCount }}
          </div>
          <div class="kpi-label">入库通过</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">
          <el-icon :size="24">
            <CircleClose />
          </el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">
            {{ rejectCount }}
          </div>
          <div class="kpi-label">已驳回</div>
        </div>
      </div>
      <div class="kpi-card">
        <div class="kpi-icon">
          <el-icon :size="24">
            <Histogram />
          </el-icon>
        </div>
        <div class="kpi-info">
          <div class="kpi-value">{{ passRate }}%</div>
          <div class="kpi-label">通过率</div>
        </div>
      </div>
    </div>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>审核历史记录</span>
          <el-button type="primary" size="small" @click="loadData"> 刷新 </el-button>
        </div>
      </template>
      <el-table v-loading="loading" :data="historyList" border>
        <el-table-column prop="id" label="审核编号" width="100" />
        <el-table-column prop="question" label="审核问题" min-width="200" />

        <el-table-column prop="answer" label="标准化答案" min-width="200">
          <template #default="{ row }">
            <span style="color: #bfbfbf">{{ row.answer || '暂无' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="result" label="审核结果" width="120">
          <template #default="{ row }">
            <el-tag :type="row.result === 'pass' ? 'primary' : 'info'" effect="dark">
              <el-icon style="margin-right: 2px">
                <CircleCheck v-if="row.result === 'pass'" />
                <CircleClose v-else />
              </el-icon>
              {{ row.result === 'pass' ? '入库' : '驳回' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="operator" label="操作管理员" width="120">
          <template #default="{ row }">
            <div style="display: flex; align-items: center; gap: 6px">
              <el-avatar :size="24" style="background: #f1f5f9; color: #1677ff; font-size: 12px">
                {{ (row.operator || '?').charAt(0).toUpperCase() }}
              </el-avatar>
              <span>{{ row.operator || '-' }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="审核时间" width="180">
          <template #default="{ row }">
            <span style="color: #bfbfbf">{{ row.created_at || '-' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        :page-sizes="[10, 20, 50]"
        layout="total, sizes, prev, pager, next"
        style="margin-top: 16px; justify-content: flex-end; display: flex"
        @current-change="loadData"
        @size-change="loadData"
      />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { DataLine, CircleCheck, CircleClose, Histogram } from '@element-plus/icons-vue'
import { getAuditHistory, type AuditLogItem } from '@/api/audit'

const historyList = ref<AuditLogItem[]>([])
const loading = ref(false)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const passCount = computed(() => historyList.value.filter((r) => r.result === 'pass').length)
const rejectCount = computed(() => historyList.value.filter((r) => r.result !== 'pass').length)
const passRate = computed(() => {
  const sum = passCount.value + rejectCount.value
  if (!sum) return 0
  return Math.round((passCount.value / sum) * 100)
})

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

<style scoped>
.audit-history-wrap {
  padding: 20px;
}
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.kpi-card {
  background: #fff;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;

  transition: transform 0.2s;
}
.kpi-card:hover {
  border-color: #cbd5e1;
}
.kpi-icon {
  width: 48px;
  height: 48px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  background: #f1f5f9;
  color: #1677ff;
}
.kpi-value {
  font-size: 24px;
  font-weight: 700;
  color: #0f172a;
}
.kpi-label {
  font-size: 13px;
  color: #bfbfbf;
  margin-top: 2px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
</style>
