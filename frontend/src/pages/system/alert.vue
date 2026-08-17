<template>
  <div class="alert-wrap">
    <el-card class="full-card">
      <div class="card-body-inner">
        <h3>异常告警</h3>

        <div class="filter-bar">
          <el-select v-model="filterStatus" placeholder="状态筛选" clearable style="width: 140px" @change="handleSearch">
            <el-option label="未确认" value="open" />
            <el-option label="已确认" value="acked" />
          </el-select>
          <el-select v-model="filterSeverity" placeholder="级别筛选" clearable style="width: 140px; margin-left: 12px" @change="handleSearch">
            <el-option label="P0 紧急" value="P0" />
            <el-option label="P1 严重" value="P1" />
            <el-option label="P2 提醒" value="P2" />
          </el-select>
          <el-button type="primary" style="margin-left: 12px" @click="handleSearch">搜索</el-button>
          <el-button style="margin-left: 8px" @click="handleReset">重置</el-button>
        </div>

        <el-table border :max-height="'calc(100vh - 320px)'" :data="tableData">
          <el-table-column prop="id" label="ID" width="70" />
          <el-table-column label="级别" width="80">
            <template #default="{ row }">
              <el-tag :type="severityTagType(row.severity)">{{ row.severity }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="rule_id" label="规则" width="180" show-overflow-tooltip />
          <el-table-column prop="message" label="告警内容" min-width="300" show-overflow-tooltip />
          <el-table-column label="当前值" width="100">
            <template #default="{ row }">
              {{ row.current_value != null ? Number(row.current_value).toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="阈值" width="100">
            <template #default="{ row }">
              {{ row.threshold_value != null ? Number(row.threshold_value).toFixed(2) : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'open' ? 'danger' : 'info'">
                {{ row.status === 'open' ? '未确认' : '已确认' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="acked_by" label="确认人" width="100" />
          <el-table-column prop="created_at" label="触发时间" width="170" />
          <el-table-column label="操作" width="100" fixed="right">
            <template #default="{ row }">
              <el-button v-if="row.status === 'open'" type="primary" size="small" @click="handleAck(row.id)">确认</el-button>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :page-sizes="[10, 50, 100]"
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
import { getAlertList, ackAlert, type AlertEventItem } from '@/api/system'

const filterStatus = ref('')
const filterSeverity = ref('')
const page = ref(1)
const pageSize = ref(20)
const tableData = ref<AlertEventItem[]>([])
const total = ref(0)

const severityTagType = (s: string) => {
  if (s === 'P0') return 'danger'
  if (s === 'P1') return 'warning'
  return 'info'
}

const loadData = async () => {
  try {
    const res = await getAlertList({
      page: page.value,
      page_size: pageSize.value,
      status: filterStatus.value || undefined,
      severity: filterSeverity.value || undefined
    })
    tableData.value = res.items
    total.value = res.total
  } catch {
    ElMessage.error('加载告警列表失败')
  }
}

const handleSearch = () => {
  page.value = 1
  loadData()
}

const handleReset = () => {
  filterStatus.value = ''
  filterSeverity.value = ''
  page.value = 1
  loadData()
}

const handleAck = async (alertId: number) => {
  try {
    await ackAlert(alertId)
    ElMessage.success('告警已确认')
    loadData()
  } catch {
    ElMessage.error('确认失败')
  }
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.alert-wrap {
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
</style>